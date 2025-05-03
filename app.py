

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS, cross_origin
import requests
from bs4 import BeautifulSoup as bs
from urllib.request import Request, urlopen
import logging

logging.basicConfig(filename="scrapper.log", level=logging.INFO)

app = Flask(__name__)

@app.route("/", methods=['GET'])
def homepage():
    return render_template("index.html")

@app.route("/review", methods=['POST', 'GET'])
def review():
    if request.method == 'POST':
        try:
            # Get search term and build URL
            searchString = request.form['content'].strip().replace(" ", "")
            flipkart_url = "https://www.flipkart.com/search?q=" + searchString
            
            # Set headers to mimic a browser request
            headers = {
                "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                               "AppleWebKit/537.36 (KHTML, like Gecko) "
                               "Chrome/115.0.0.0 Safari/537.36")
            }
            
            req = Request(flipkart_url, headers=headers)
            uClient = urlopen(req)
            flipkartPage = uClient.read()
            uClient.close()
            flipkart_html = bs(flipkartPage, "html.parser")

            # Find the product boxes
            bigboxes = flipkart_html.find_all("div", {"class": "cPHDOP col-12-12"})
            if not bigboxes or len(bigboxes) <= 3:
                logging.error("Not enough product boxes found.")
                return render_template('error.html', message="Product boxes not found")
            # Remove non-product boxes (first three)
            del bigboxes[0:3]
            box = bigboxes[0]
            productLink = "https://www.flipkart.com" + box.div.div.div.a['href']
            
            # Get the product page
            prodRes = requests.get(productLink, headers=headers)
            prodRes.encoding = 'utf-8'
            prod_html = bs(prodRes.text, "html.parser")
            logging.info("Product page fetched successfully")
            
            # Extract review/comment boxes
            commentboxes = prod_html.find_all('div', {'class': "RcXBOT"})
            if not commentboxes:
                logging.error("No comment boxes found.")
                return render_template('error.html', message="No reviews found for this product")
            
            reviews = []
            for commentbox in commentboxes:
                # Extract reviewer's name
                try:
                    name = commentbox.div.div.find_all('p', {'class': '_2NsDsF AwS1CA'})[0].text.strip()
                except Exception as e:
                    logging.info("Name exception: %s", e)
                    name = "No Name"
                    
                # Extract rating
                try:
                    rating = commentbox.div.div.div.div.text.strip()
                except Exception as e:
                    logging.info("Rating exception: %s", e)
                    rating = "No Rating"
                    
                # Extract comment heading
                try:
                    commentHead = commentbox.div.div.div.p.text.strip()
                except Exception as e:
                    logging.info("Comment heading exception: %s", e)
                    commentHead = "No Comment Heading"
                    
                # Extract comment text (with default if not found)
                try:
                    comtags = commentbox.div.div.find_all('div', {'class': ''})
                    if comtags and len(comtags) > 0:
                        custComment = comtags[0].div.text.strip()
                    else:
                        custComment = "No Comment"
                except Exception as e:
                    logging.info("Customer comment exception: %s", e)
                    custComment = "No Comment"
                    
                review_dict = {
                    "Product": searchString,
                    "Name": name,
                    "Rating": rating,
                    "CommentHead": commentHead,
                    "Comment": custComment
                }
                reviews.append(review_dict)
            
            logging.info("Final reviews: %s", reviews)
            if reviews:
                return render_template('result.html', reviews=reviews)
            else:
                return render_template('error.html', message="No reviews captured")
        except Exception as e:
            logging.exception("An error occurred during the review extraction process")
            return render_template('error.html', message="Something went wrong. Please try again later.")
    else:
        return render_template('index.html')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
