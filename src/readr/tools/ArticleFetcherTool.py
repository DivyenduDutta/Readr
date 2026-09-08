from trafilatura import extract, fetch_url

from readr.constants.tool_constants import ToolDescriptions, ToolNames
from readr.utils.singleton import SingletonMeta


class ArticleFetcherTool(metaclass=SingletonMeta):
    """
    Fetches the contents of an online article provided the URL is given.
    """

    def __init__(self):
        self.tool_name = ToolNames.ARTICLE_FETCHER.value
        self.tool_description = ToolDescriptions.ARTICLE_FETCHER_DESC.value
        self.url = None
        self.article_content = None

    def execute(self, url: str) -> str:
        if self.url == url:
            return self.article_content if self.article_content is not None else ""
        self.url = url
        page = fetch_url(self.url)
        self.article_content = extract(page)
        return self.article_content if self.article_content is not None else ""
