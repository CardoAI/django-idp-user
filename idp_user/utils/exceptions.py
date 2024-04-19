class UnsupportedAppEntityType(Exception):
    def __init__(self, app_entity_type):
        super().__init__(f"Unsupported app entity type: {str(app_entity_type)}")
