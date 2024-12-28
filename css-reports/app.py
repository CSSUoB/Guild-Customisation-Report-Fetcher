from flask import Flask, request, send_file, jsonify, redirect
from report import get_product_customisations
import os
import re

app = Flask("css-reports")

@app.route('/')
def hello():
    return redirect("https://cssbham.com", code=302)

@app.route('/customisation_report', methods=['GET'])
async def fetch_customisation_report():
    # Retrieve query parameters
    auth_cookie = request.args.get('auth_cookie')
    organisation_id = request.args.get('organisation_id')
    product_name = request.args.get('product_name')

    # print("Auth cookie: " + auth_cookie)
    print("Organisation ID: " + organisation_id)
    print("Product Name: " + product_name)

    # Validate parameters
    if not auth_cookie or not organisation_id or not product_name:
        return jsonify({"error": "Missing required parameters."}), 400
    
    product_name = re.sub(r'\W+', '', product_name)

    csv_file_path: str | None = None

    try:
        # Generate the CSV file
        csv_file_path = await get_product_customisations(product_id_or_name=product_name, auth_cookie=auth_cookie, org_id=organisation_id)

        if not csv_file_path:
            print("Failed to generate the customisation report")
            return jsonify({"error": "Failed to generate the customisation report"}), 500

        # Return the file as a response
        return send_file(csv_file_path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Clean up the generated file
        if csv_file_path and os.path.exists(csv_file_path):
            os.remove(csv_file_path)

if __name__ == '__main__':
    # from waitress import serve
    app.run(host='0.0.0.0', port=8000)
