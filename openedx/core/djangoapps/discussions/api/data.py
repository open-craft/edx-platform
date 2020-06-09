import attr


@attr.s(frozen=True)
class DiscussionConfigData:
    """
    Discussion Configuration Data Object
    """

    provider = attr.ib(type=str)
    config_key = attr.ib(type=str)
    config = attr.ib(type=dict)
