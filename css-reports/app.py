from flask import Flask, request, send_file, jsonify, redirect
from report import get_product_customisations
from dotenv import set_key
import os

app = Flask(__name__)

@app.route('/')
def hello():
    return redirect("https://cssbham.com", code=302)

@app.route('/customisation_report', methods=['GET'])
async def fetch_customisation_report():
    # Retrieve query parameters
    auth_cookie = request.args.get('auth_cookie')
    organisation_id = request.args.get('organisation_id')
    product_name = request.args.get('product_name')

    print("Auth cookie: " + auth_cookie)

    # Validate parameters
    if not auth_cookie or not organisation_id:
        return jsonify({"error": "Missing required parameters."}), 400

    set_key('.env', 'ORGANISATION_ADMIN_TOKEN', auth_cookie)
    set_key('.env', 'ORGANISATION_ID', organisation_id)

    try:
        # Generate the CSV file
        csv_file_path = await get_product_customisations(product_name)

        if not csv_file_path:
            return jsonify({"error": "Failed to generate the customisation report"}), 500

        # Return the file as a response
        return send_file(csv_file_path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Clean up the generated file
        if os.path.exists(csv_file_path):
            os.remove(csv_file_path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
