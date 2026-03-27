class BaseRepository:
    def __init__(self, model_class):
        self.model_class = model_class

    def create(self, **kwargs):
        instance = self.model_class(**kwargs)
        instance.save()
        return instance

    def read(self, id):
        return self.model_class.objects.get(id=id)

    def update(self, id, **kwargs):
        instance = self.read(id)
        for key, value in kwargs.items():
            setattr(instance, key, value)
        instance.save()
        return instance

    def delete(self, id):
        instance = self.read(id)
        instance.delete()