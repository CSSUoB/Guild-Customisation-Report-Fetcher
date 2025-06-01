# Guild Customisation Report Fetcher

This project provides a Flask-based web API to fetch customisation, purchaser, or sales reports from the Guild website.

## Prerequisites

- Python 3.12+ (or use Docker)
- `pip` for installing dependencies

## Setup

### 1. Install Dependencies

If running locally, install the required Python packages:

```sh
pip install -r requirements.txt
```

### 2. Environment

No special environment variables are required. You will need a valid `auth_cookie` for the Guild website.

## Running the Server

### Option 1: Locally

Run the Flask app:

```sh
python app.py
```

The server will start on `http://0.0.0.0:8000`.

### Option 2: Using Docker

Build and run the Docker container:

```sh
docker build -t css-reports .
docker run -p 8000:8000 css-reports
```

## API Usage

### Endpoint

```http
GET /customisation_report
```

### Query Parameters

- `auth_cookie` (required): Authentication cookie for the Guild website.
- `organisation_id` (required): Organisation ID for the report.
- `report_type` (optional): One of `Customisations`, `Purchasers`, or `Sales`. Defaults to `Customisations`.
- `product_name` or `product_names` (required): Name or ID of the product to filter.
- `start_date` (optional): Start date in `YYYY-MM-DD` format. Defaults to `2000-01-01`.
- `end_date` (optional): End date in `YYYY-MM-DD` format. Defaults to `2100-01-01`.

**Note:** You must provide either `product_name` or `product_names`, but not both.

### Example Request

```sh
curl "http://localhost:8000/customisation_report?auth_cookie=YOUR_COOKIE&organisation_id=1234&product_name=Hoodie&start_date=2024-01-01&end_date=2024-12-31"
```

This will return a CSV file as a download containing the requested report.

### Error Handling

- Returns HTTP 400 for missing or invalid parameters.
- Returns HTTP 500 for server or report generation errors.

## Other Endpoints

- `/` and any unknown route: Redirects to https://cssbham.com

---

**Tip:** For production, consider using a WSGI server like `waitress` or `gunicorn` instead of Flask's built-in server.
