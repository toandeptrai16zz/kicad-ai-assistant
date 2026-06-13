try:
    from .plugin_action import AiAssistantPlugin
    AiAssistantPlugin().register()
except Exception as e:
    import logging
    logging.error(f"Failed to register KiCad AI Assistant Plugin: {e}")
