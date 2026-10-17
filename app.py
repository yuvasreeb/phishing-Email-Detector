import re
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify, render_template
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix

app = Flask(__name__)

KW = ["urgent","verify","password","account","suspended","click here","login",
      "bank","confirm","winner","free","limited time","security alert","update"]

def extra(t):
    l = t.lower()
    urls = re.findall(r'https?://\S+', l)
    ip = sum(bool(re.search(r'//\d+\.\d+\.\d+\.\d+', u)) for u in urls)
    return [len(urls), ip, sum(k in l for k in KW), t.count('!')]

# ---- Load dataset and train ----
df = pd.read_csv('Phishing_Email.csv').dropna()
df['y'] = (df['Email Type'] == 'Phishing Email').astype(int)

X_tr, X_te, y_tr, y_te = train_test_split(
    df['Email Text'], df['y'], test_size=0.2, random_state=42, stratify=df['y'])

vec = TfidfVectorizer(max_features=5000, stop_words='english')

def build(texts, fit=False):
    texts = list(texts)
    tf = vec.fit_transform(texts) if fit else vec.transform(texts)
    return hstack([tf, csr_matrix(np.array([extra(t) for t in texts]))]).tocsr()

model = LogisticRegression(max_iter=1000)
model.fit(build(X_tr, fit=True), y_tr)
pred = model.predict(build(X_te))
ACC = round(accuracy_score(y_te, pred) * 100, 2)
CM = confusion_matrix(y_te, pred, labels=[0, 1]).tolist()
print("Accuracy:", ACC, "Confusion matrix:", CM)

# ---- Routes ----
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/metrics')
def metrics():
    return jsonify(accuracy=ACC, cm=CM)

@app.route('/predict', methods=['POST'])
def predict():
    text = request.get_json().get('text', '')
    p = model.predict_proba(build([text]))[0][1]
    urls, ip, kws, ex = extra(text)
    phishing = p >= 0.5
    return jsonify(label="Phishing" if phishing else "Safe",
                   confidence=round((p if phishing else 1 - p) * 100),
                   urls=urls, ip_urls=ip, keywords=kws, exclamations=ex)

if __name__ == '__main__':
    app.run(debug=True)