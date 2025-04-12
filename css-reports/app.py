from flask import Flask, request, send_file, jsonify, redirect
from report import get_product_customisations
from datetime import datetime
import os
import re

app = Flask("css-reports")


@app.route("/")
def hello():
    return redirect("https://cssbham.com", code=302)


@app.errorhandler(404)
def page_not_found(e: Exception | int):
    print(e)
    return redirect("https://cssbham.com", code=302)


@app.route("/customisation_report", methods=["GET"])
async def fetch_customisation_report():
    # Retrieve query parameters
    auth_cookie: str | None = request.args.get("auth_cookie")
    organisation_id: str | None = request.args.get("organisation_id")
    product_name: str | None = request.args.get("product_name")
    product_names: str | None = request.args.get("product_names")
    start_date: str | None = request.args.get("start_date")
    end_date: str | None = request.args.get("end_date")

    # print("Auth cookie: " + auth_cookie)
    print(f"Organisation ID: {organisation_id}")
    print(f"Product Name: {product_name}")

    if (not auth_cookie or not organisation_id):
        return jsonify({"error": "An auth token and organisation id are required."}), 400
    
    if ((not product_name) and (not product_names)):
        return jsonify({"error": "Either product_name or product_names is required."}), 400

    if product_name and product_names:
        return jsonify({"error": "Both product_name and product_names cannot be provided."}), 400
    
    start_date_dt: datetime
    end_date_dt: datetime

    try:
        start_date_dt = datetime.strptime(start_date or "2000-01-01", "%Y-%m-%d")
        end_date_dt = datetime.strptime(end_date or "2100-01-01", "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    name_or_id: str = product_name or product_names  # type: ignore[assignment]
    name_or_id = re.sub(r"\W\s", "", name_or_id)

    csv_file_path: str | None = None

    try:
        # Generate the CSV file
        csv_file_path = await get_product_customisations(
            product_id_or_name=name_or_id,
            auth_cookie=auth_cookie,
            org_id=organisation_id,
            from_date_input=start_date_dt,
            to_date_input=end_date_dt,
        )

        if not csv_file_path:
            print("Failed to generate the customisation report")
            return jsonify(
                {"error": "Failed to generate the customisation report"}
            ), 500

        # Return the file as a response
        return send_file(csv_file_path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Clean up the generated file
        if csv_file_path and os.path.exists(csv_file_path):
            os.remove(csv_file_path)


if __name__ == "__main__":
    # from waitress import serve
    app.run(host="0.0.0.0", port=8000, debug=True)
