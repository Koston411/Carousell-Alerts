import json

class Classified_item():
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=False, indent=4)

    def __init__(self):
        self.platform = ''
        self.listing_id = ''
        self.title = ''
        self.price = ''
        self.image = ''
        self.seller = ''
        self.url = ''
