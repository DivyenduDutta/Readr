from typing import Any

from trafilatura import extract, fetch_url

from readr.constants.tool_constants import ToolDescriptions, ToolNames
from readr.utils.singleton import SingletonMeta


class ArticleFetcherTool(metaclass=SingletonMeta):
    """
    Fetches the contents of an online article provided the URL is given.
    """

    def __init__(self):
        self.url = None
        self.article_content = None

    def execute(self, url: str) -> str:
        """
        The main logic of the article fetcher tool. Uses Trafilatura to fetch the online article
        and extracts the text from it.

        Args:
            url (str): The url of the online article whose contents need to be fetched.

        Returns:
            str: The contents of the online article.
        """
        if self.url == url:
            return self.article_content if self.article_content is not None else ""
        self.url = url
        page = fetch_url(self.url)
        self.article_content = extract(page)
        return self.article_content if self.article_content is not None else ""

    @staticmethod
    def get_tool_description() -> dict[str, Any]:
        """
        Returns the description of the article fetcher tool. To be used by the LLM.

        Returns:
            dict[str, Any] : The tool description.
        """
        tool_desc = {
            "type": "function",
            "name": f"{ToolNames.ARTICLE_FETCHER.value}",
            "description": f"{ToolDescriptions.ARTICLE_FETCHER_DESC.value}",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to fetch the contents of.",
                    },
                },
                "required": ["url"],
            },
        }
        return tool_desc
