from flask import Flask, request, jsonify
from langchain_huggingface import HuggingFaceEmbeddings
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure


app = Flask(__name__)

cred = credentials.Certificate("./junction-2024-firebase-adminsdk-nkyl9-f1b4744457.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

embed_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-l6-v2")



@app.route("/get_articles", methods=["GET"])
def get_articles():
    # Reference the 'news_articles' collection
    articles_ref = db.collection("news_articles")
    docs = articles_ref.stream()

    # Prepare a list to store all articles
    articles = []

    # Iterate through each document and add it to the list
    for doc in docs:
        article_data = doc.to_dict()
        article_data["id"] = doc.id  # Include the document ID
        articles.append(article_data)

    # Return the list of articles as a JSON response
    return jsonify({"articles": articles})


@app.route("/get_article/<article_id>", methods=["GET"])
def get_article(article_id):
    doc_ref = db.collection("news_articles").document(article_id)
    doc = doc_ref.get()
    if doc.exists:
        return jsonify({"article": doc.to_dict(), "id": doc.id})
    else:
        return jsonify({"error": "Article not found"}), 404
    

    

@app.route("/embed_text", methods=["POST"])
def embed_text():
    data = request.json
    user_input = data.get("text", "")
    # Embed the user input
    response = embed_model.embed_query(user_input)
    
    return jsonify({"embedded_text": response})


@app.route("/add_article", methods=["POST"])
def add_article():
    data = request.json

    article = data.get("article", "")
    subtopic = data.get("topic", "")
    statements = data.get("statements", "")

    embedded_subtopic = embed_model.embed_query(subtopic)

    news_doc = { 
        "topic" : subtopic,
        "article": article,
        "statements": statements,
        "embedded_subtopic": Vector(embedded_subtopic)
        }

    db.collection("news").document("1").set(news_doc)

    return jsonify({"response": "success"})


@app.route("/similarity_search_article", methods=["POST"])
def similarity_search_article():
    data = request.json
    subtopic = data.get("topic", "")
    embedded_subtopic = embed_model.embed_query(subtopic)

    collection = db.collection("news")

    # Requires a single-field vector index
    vector_query = collection.find_nearest(
        vector_field="embedded_subtopic",
        query_vector=Vector(embedded_subtopic),
        distance_measure=DistanceMeasure.COSINE,
        limit=5,
        distance_result_field="vector_distance"
    )

    docs = vector_query.stream()

    response_data = [f"{doc.id}), Distance: {doc.get('vector_distance')}" for doc in docs]

    return jsonify({"response": response_data})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
