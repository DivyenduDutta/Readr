from enum import Enum


class ToolNames(Enum):
    """
    Names of the custom tools, used as the function name declared to the LLM.
    """

    ARTICLE_FETCHER = "article_fetcher"


class ToolDescriptions(Enum):
    """
    Descriptions of the custom tools, shown to the LLM so it knows when to use them.
    """

    ARTICLE_FETCHER_DESC = """
        This tool should be used to retrieve the contents of an online article in text format.
        This tool requires the URL of the online article whose content needs to be fetched.
        """
