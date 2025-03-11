from flask import Flask, request, jsonify
from flask_cors import CORS
from unstructured.partition.auto import partition
import requests
import tempfile
import os
import ocrmypdf
import pymupdf4llm

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Health check endpoint
@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"})

def extract_text_from_url(file_url: str) -> str:
    try:
        file_extension = os.path.splitext(file_url)[-1].lower()
        if file_extension == ".pdf":
            response = requests.get(file_url)
            response.raise_for_status()
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                temp_file.write(response.content)
                temp_file_path = temp_file.name

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as output_file:
                output_pdf_path = output_file.name

            ocrmypdf.ocr(
                temp_file_path,
                output_pdf_path,
                skip_text=True,
                jobs=1,
                optimize=0,
                output_type="pdf",
                fast_web_view=999999,
                language="eng+ara"
            )
            extracted_text = pymupdf4llm.to_markdown(output_pdf_path)
            os.remove(temp_file_path)
            os.remove(output_pdf_path)
        else:
            elements = partition(url=file_url, languages=["eng", "ara"])
            extracted_text = "\n".join(str(element) for element in elements)
        return extracted_text
    except Exception as e:
        return f"Failed to extract text: {str(e)}"

@app.route("/extract-text", methods=["POST"])
def extract_text_from_url_endpoint():
    request_body = request.get_json()
    file_url = request_body.get("file_url")
    if not file_url:
        return jsonify({"error": "file_url is required in the request body"}), 400
    
    try:
        extracted_text = extract_text_from_url(file_url)
        return jsonify({"extracted_text": extracted_text})
    except Exception as e:
        return jsonify({"error": f"Failed to process file: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
