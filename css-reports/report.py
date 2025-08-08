"""Python script to fetch a customisation report from the Guild website."""

import re
from datetime import datetime

from typing import Final, Mapping, TYPE_CHECKING
import aiohttp
import bs4
from bs4 import BeautifulSoup


if TYPE_CHECKING:
    from http.cookies import Morsel

BASE_HEADERS: Final[Mapping[str, str]] = {
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Expires": "0",
}

SALES_FROM_DATE_KEY: Final[str] = (
    "ctl00$ctl00$Main$AdminPageContent$drDateRange$txtFromDate"
)
SALES_FROM_TIME_KEY: Final[str] = (
    "ctl00$ctl00$Main$AdminPageContent$drDateRange$txtFromTime"
)
SALES_TO_DATE_KEY: Final[str] = (
    "ctl00$ctl00$Main$AdminPageContent$drDateRange$txtToDate"
)
SALES_TO_TIME_KEY: Final[str] = (
    "ctl00$ctl00$Main$AdminPageContent$drDateRange$txtToTime"
)


async def get_msl_context(
    url: str, auth_cookie: str
) -> tuple[dict[str, str], dict[str, str]]:
    """Get the required context headers, data and cookies to make a request to MSL."""

    BASE_COOKIES: Mapping[str, str] = {
        ".ASPXAUTH": auth_cookie,
    }

    http_session: aiohttp.ClientSession = aiohttp.ClientSession(
        headers=BASE_HEADERS,
        cookies=BASE_COOKIES,
    )
    data_fields: dict[str, str] = {}
    cookies: dict[str, str] = {}
    async with http_session, http_session.get(url=url) as field_data:
        data_response = BeautifulSoup(
            markup=await field_data.text(),
            features="html.parser",
        )

        for field in data_response.find_all(name="input"):
            if isinstance(field, bs4.Tag):
                if field.get("name") and field.get("value"):
                    data_fields[str(field.get("name"))] = str(field.get("value"))

        for cookie in field_data.cookies:
            cookie_morsel: Morsel[str] | None = field_data.cookies.get(cookie)
            if cookie_morsel is not None:
                cookies[cookie] = cookie_morsel.value
        cookies[".ASPXAUTH"] = auth_cookie

    if "Login" in data_response.title.string:  # type: ignore[union-attr, operator]
        print("Redirected to login page!")
        print(url)
        raise ValueError("Redirected to login page!")

    print(f"Successfully retrieved the requested context with url: {url}")

    return data_fields, cookies


async def fetch_report_url_and_cookies(
    auth_cookie: str,
    org_id: str,
    from_date: datetime,
    to_date: datetime,
    report_type: str,
) -> tuple[str | None, dict[str, str]]:
    """Fetch the specified report from the guild website."""
    SALES_REPORTS_URL: Final[str] = (
        f"https://www.guildofstudents.com/organisation/salesreports/{org_id}/"
    )

    data_fields, cookies = await get_msl_context(url=SALES_REPORTS_URL, auth_cookie=auth_cookie)

    form_data: dict[str, str] = {
        SALES_FROM_DATE_KEY: from_date.strftime("%d/%m/%Y"),
        SALES_FROM_TIME_KEY: from_date.strftime("%H:%M"),
        SALES_TO_DATE_KEY: to_date.strftime("%d/%m/%Y"),
        SALES_TO_TIME_KEY: to_date.strftime("%H:%M"),
        "__EVENTTARGET": f"ctl00$ctl00$Main$AdminPageContent$lb{report_type}",
        "__EVENTARGUMENT": "",
    }

    # data_fields.pop("ctl00$ctl00$search$btnSubmit")
    # data_fields.pop("ctl00$ctl00$ctl17$btnSubmit")

    data_fields.update(form_data)

    session_v2: aiohttp.ClientSession = aiohttp.ClientSession(
        headers=BASE_HEADERS,
        cookies=cookies,
    )
    async with (
        session_v2,
        session_v2.post(url=SALES_REPORTS_URL, data=data_fields) as http_response
    ):
        if http_response.status != 200:
            print("Returned a non 200 status code!!")
            print(http_response)
            return None, {}

        response_html: str = await http_response.text()

    soup = BeautifulSoup(response_html, "html.parser")
    report_viewer_div: bs4.PageElement | bs4.Tag | bs4.NavigableString | None = (
        soup.find("div", {"id": "report_viewer_wrapper"})
    )
    if not report_viewer_div or report_viewer_div.text.strip() == "":
        print("Failed to load the reports.")
        print(report_viewer_div)
        raise ValueError("Failed to load the reports.")

    if "no transactions" in response_html:
        print("No transactions were found!")
        raise ValueError("No transactions were found!")

    match = re.search(r'ExportUrlBase":"(.*?)"', response_html)
    if not match:
        print("Failed to find the report export url from the http response.")
        print(response_html)
        raise ValueError("Failed to find the report export url from the http response.")

    urlbase: str = match.group(1).replace(r"\u0026", "&").replace("\\/", "/")
    if not urlbase:
        print("Failed to construct report url!")
        print(match)
        raise ValueError("Failed to construct report url!")

    return f"https://guildofstudents.com/{urlbase}CSV", cookies


async def get_product_customisations(
    product_id_or_name: str,
    auth_cookie: str,
    org_id: str,
    from_date_input: datetime,
    to_date_input: datetime,
    report_type: str,
) -> str:
    """Get the customisation report for a specific product."""
    report_url, cookies = await fetch_report_url_and_cookies(
        auth_cookie=auth_cookie,
        org_id=org_id,
        from_date=from_date_input,
        to_date=to_date_input,
        report_type=report_type,
    )

    if report_url is None:
        print("Failed to retrieve customisations report URL.")
        raise ValueError("Failed to retrieve customisations report URL.")

    file_session: aiohttp.ClientSession = aiohttp.ClientSession(
        headers=BASE_HEADERS,
        cookies=cookies,
    )
    async with file_session, file_session.get(url=report_url) as file_response:
        if file_response.status != 200:
            print("Customisation report file session returned a non 200 status code.")
            print(file_response)
            raise ValueError(
                "Customisation report file session returned a non 200 status code."
            )

        print("Successfully retrieved customisation report: " + product_id_or_name)

        # save the csv file
        with open("customisations.csv", "wb") as file:
            for _ in range(4):
                file.write(await file_response.content.readline())

            # write the rest of the file, but only if the line contains the product
            async for line in file_response.content:
                line_data: str = line.decode("utf-8").split(",")[0].strip()
                if product_id_or_name in line_data:
                    file.write(line)

        return file.name
