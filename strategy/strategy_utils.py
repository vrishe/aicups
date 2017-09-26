class EnumBase:
    class EnumError(TypeError): pass
    def __setattr__(self,name,value):
        raise self.EnumError, 'Can\'t modify enum attribute: %s.'%name