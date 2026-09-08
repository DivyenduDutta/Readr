from enum import Enum


class ToolNames(Enum):
    ARTICLE_FETCHER = "Article Fetcher"


class ToolDescriptions(Enum):
    ARTICLE_FETCHER_DESC = """
        This tool should be used to retrieve the contents of an online article in text format.
        This tool requires the URL of the online article whose content needs to be fetched.
        """
