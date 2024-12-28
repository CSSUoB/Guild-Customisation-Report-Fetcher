"""Python script to fetch a customisation report from the Guild website."""

from typing import Final, Mapping, TYPE_CHECKING
import aiohttp
import bs4
from bs4 import BeautifulSoup
import re
import sys
from datetime import datetime, timedelta

from dotenv import dotenv_values

if TYPE_CHECKING:
    from http.cookies import Morsel

CONFIG: Final[dict[str, str]] = dotenv_values(".env")  # type: ignore[assignment]

BASE_HEADERS: Final[Mapping[str, str]] = {
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Expires": "0",
}

BASE_COOKIES: Final[Mapping[str, str]] = {
    ".ASPXAUTH": CONFIG["ORGANISATION_ADMIN_TOKEN"],
}

ORGANISATION_ID: Final[str] = CONFIG["ORGANISATION_ID"]

SALES_REPORTS_URL: Final[str] = f"https://www.guildofstudents.com/organisation/salesreports/{ORGANISATION_ID}/"
SALES_FROM_DATE_KEY: Final[str] = "ctl00$ctl00$Main$AdminPageContent$drDateRange$txtFromDate"
SALES_FROM_TIME_KEY: Final[str] = "ctl00$ctl00$Main$AdminPageContent$drDateRange$txtFromTime"
SALES_TO_DATE_KEY: Final[str] = "ctl00$ctl00$Main$AdminPageContent$drDateRange$txtToDate"
SALES_TO_TIME_KEY: Final[str] = "ctl00$ctl00$Main$AdminPageContent$drDateRange$txtToTime"

TODAYS_DATE: datetime = datetime.now()
from_date: datetime = TODAYS_DATE - timedelta(weeks=1200)
to_date: datetime = TODAYS_DATE + timedelta(weeks=52)


async def get_msl_context(url: str) -> tuple[dict[str, str], dict[str, str]]:
    """Get the required context headers, data and cookies to make a request to MSL."""
    http_session: aiohttp.ClientSession = aiohttp.ClientSession(
        headers=BASE_HEADERS,
        cookies=BASE_COOKIES,
    )
    data_fields: dict[str, str] = {}
    cookies: dict[str ,str] = {}
    async with http_session, http_session.get(url=url) as field_data:
        data_response = BeautifulSoup(
            markup=await field_data.text(),
            features="html.parser",
        )

        for field in data_response.find_all(name="input"):
            if field.get("name") and field.get("value"):
                data_fields[field.get("name")] = field.get("value")

        for cookie in field_data.cookies:
            cookie_morsel: Morsel[str] | None = field_data.cookies.get(cookie)
            if cookie_morsel is not None:
                cookies[cookie] = cookie_morsel.value
        cookies[".ASPXAUTH"] = CONFIG["ORGANISATION_ADMIN_TOKEN"]

    if "Login" in data_response.title.string:  # type: ignore[union-attr, operator]
        print("Redirected to login page!")
        print(url)
        sys.exit(1)

    return data_fields, cookies


async def fetch_report_url_and_cookies() -> tuple[str | None, dict[str, str]]:  # noqa: E501
    """Fetch the specified report from the guild website."""
    data_fields, cookies = await get_msl_context(url=SALES_REPORTS_URL)

    form_data: dict[str, str] = {
        SALES_FROM_DATE_KEY: from_date.strftime("%d/%m/%Y"),
        SALES_FROM_TIME_KEY: from_date.strftime("%H:%M"),
        SALES_TO_DATE_KEY: to_date.strftime("%d/%m/%Y"),
        SALES_TO_TIME_KEY: to_date.strftime("%H:%M"),
        "__EVENTTARGET": "ctl00$ctl00$Main$AdminPageContent$lbCustomisations",
        "__EVENTARGUMENT": "",
    }

    data_fields.pop("ctl00$ctl00$search$btnSubmit")
    data_fields.pop("ctl00$ctl00$ctl17$btnSubmit")

    data_fields.update(form_data)

    session_v2: aiohttp.ClientSession = aiohttp.ClientSession(
        headers=BASE_HEADERS,
        cookies=cookies,
    )
    async with session_v2, session_v2.post(url=SALES_REPORTS_URL, data=data_fields) as http_response:  # noqa: E501
        if http_response.status != 200:
            print("Returned a non 200 status code!!")
            print(http_response)
            return None, {}

        response_html: str = await http_response.text()

    # get the report viewer div
    soup = BeautifulSoup(response_html, "html.parser")
    report_viewer_div: bs4.Tag | bs4.NavigableString | None = soup.find("div", {"id": "report_viewer_wrapper"})
    if not report_viewer_div or report_viewer_div.text.strip() == "":
        print("Failed to load the reports.")
        print(report_viewer_div)
        sys.exit(1)

    if "no transactions" in response_html:
        print("No transactions were found!")
        return None, {}

    match = re.search(r'ExportUrlBase":"(.*?)"', response_html)
    if not match:
        print("Failed to find the report export url from the http response.")
        print(response_html)
        return None, {}

    urlbase: str = match.group(1).replace(r"\u0026", "&").replace("\\/", "/")
    if not urlbase:
        print("Failed to construct report url!")
        print(match)
        return None, {}

    return f"https://guildofstudents.com/{urlbase}CSV", cookies



async def get_all_customisations() -> None:
    """Get the set of product customisations for a given product ID, checking the past year."""
    report_url, cookies = await fetch_report_url_and_cookies()

    if report_url is None:
        print("Failed to retrieve customisations report URL.")
        return

    file_session: aiohttp.ClientSession = aiohttp.ClientSession(
        headers=BASE_HEADERS,
        cookies=cookies,
    )
    async with file_session, file_session.get(url=report_url) as file_response:
        if file_response.status != 200:
            print("Customisation report file session returned a non 200 status code.")
            print(file_response)
            return

        # save the csv file
        with open("full_historical_customisations.csv", "wb") as file:
            file.write(await file_response.read())


async def get_product_customisations(product_id_or_name: str) -> None:
    report_url, cookies = await fetch_report_url_and_cookies()

    if report_url is None:
        print("Failed to retrieve customisations report URL.")
        return
    
    file_session: aiohttp.ClientSession = aiohttp.ClientSession(
        headers=BASE_HEADERS,
        cookies=cookies,
    )
    async with file_session, file_session.get(url=report_url) as file_response:
        if file_response.status != 200:
            print("Customisation report file session returned a non 200 status code.")
            print(file_response)
            return

        # save the csv file
        with open(f"{product_id_or_name.lower().replace(" ", "_")}_customisations.csv", "wb") as file:
            # write the first 5 lines
            for i in range(5):
                file.write(await file_response.content.readline())

            # write the rest of the file, but only if the line contains the product
            async for line in file_response.content:
                if product_id_or_name in line.decode("utf-8"):
                    file.write(line)


if __name__ == '__main__':
    import asyncio
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(get_product_customisations("Ball 2024"))

