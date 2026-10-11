from typing import Any

from trafilatura import extract, fetch_url

from readr.constants.tool_constants import ToolDescriptions, ToolNames
from readr.utils.singleton import SingletonMeta


class ArticleFetcherTool(metaclass=SingletonMeta):
    """
    Fetches the contents of an online article provided the URL is given.
    A singleton: the most recently fetched article is cached.

    Attributes:
        url (str | None): The url of the most recently fetched article.
        article_content (str | None): The extracted text of that article.
    """

    def __init__(self) -> None:
        self.url: str | None = None
        self.article_content: str | None = None

    def execute(self, url: str) -> str:
        """
        The main logic of the article fetcher tool. Uses Trafilatura to fetch the online article
        and extracts the text from it. Repeated calls with the same url return the cached text.

        Args:
            url (str): The url of the online article whose contents need to be fetched.

        Returns:
            str: The contents of the online article, or an empty string if no text
                 could be extracted.
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
            dict[str, Any] : The function tool declaration (type, name, description and
                             json schema of the parameters) sent to the model.
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
