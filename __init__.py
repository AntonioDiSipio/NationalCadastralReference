def classFactory(iface):
    from .ncr_plugin import NCRPlugin
    return NCRPlugin(iface)
