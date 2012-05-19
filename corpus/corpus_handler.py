import tornado.ioloop
import tornado.web
import simplejson
import pymongo

from nosy.model import ClassificationObject
import nosy.util

class CorpusHandler(tornado.web.RequestHandler):
    def get(self):
        try:
            limit = int(self.get_argument('limit', 10))
        except ValueError:
            raise tornado.web.HTTPError(400)

        query = {}

        # Search for keywords after stemming if supplied
        keywords = self.get_argument('keywords', None)
        if keywords:
            words = map(lambda k: k.lower(), keywords.split(','))
            words = map(lambda w: ClassificationObject.stem(w), words)
            query['stemmed_keywords'] = { '$all': words }

        # Search for tags if supplied
        tags = self.get_argument('tags', None)
        if tags:
            tags = map(lambda t: t.lower(), tags.split(','))
            query['tags'] = { '$all': tags }
        else:
            # Otherwise filter by tagged or untagged
            tagged = self.get_argument('tagged', False)
            if tagged:
                query['tags'] = { '$ne' : [] }
            else:
                query['tags'] = []

        results = ClassificationObject.find(
            query=query,
            limit=limit,
            sort=[("last_modified", pymongo.DESCENDING)]
        )

        dicts = [ c.to_dict() for c in results ]
        json = simplejson.dumps(dicts, default=nosy.util.json_serializer)

        self.set_header("Content-Type", "application/json")
        self.write(json)

    #  curl -X PUT -d "tags=funny" http://localhost:8888/corpus?id=<id>
    # or curl -X PUT "http://localhost:8888/corpus?id=<id>&tags=<t1,t2,...>"
    def put(self):
        try:
            doc_id = int(self.get_argument('id'))
        except ValueError:
            raise tornado.web.HTTPError(400, "Expecting integer value")

        tags = self.get_argument('tags', None)
        if tags:
            tags = map( lambda t: t.lower(), tags.split(','))

        # update the tags for classification object
        c = ClassificationObject.find_by_id(doc_id)
        if c:
            c.tags = tags
            c.save()
        else:
            raise tornado.web.HTTPError(404, "Could not find document with id %i" % doc_id)

        json = simplejson.dumps({'success': True, 'message' : "Updated document with id %i" % doc_id,
            'tags' : tags})
        self.set_header('Content-Type', 'application/json')
        self.write(json)

    # curl -X DELETE "http://localhost:8888/corpus?id=<id>&tags=<t1,t2,...>"
    def delete(self):
        try:
            doc_id = int(self.get_argument('id'))
        except ValueError:
            raise tornado.web.HTTPError(400, "Expecting integer value")

        query = {
            '_id' : doc_id
        }
        tags = self.get_argument('tags', None)
        if tags:
            tags = map( lambda t: t.lower(), tags.split(','))
            query['tags'] = tags

        c = ClassificationObject.find_by_id(doc_id)
        if c:
            res = c.remove(query)
        else:
            raise tornado.web.HTTPError(404, "Could not find document with id %i" % doc_id)

        raise tornado.web.HTTPError(200, "Document id %i successfully deleted" % doc_id)

class TagsHandler(tornado.web.RequestHandler):
    def get(self):
        tags = ClassificationObject.tags()
        
        json = simplejson.dumps({'tags' : tags})
        self.set_header("Content-Type", "application/json")
        self.write(json)

application = tornado.web.Application([
    (r'/corpus', CorpusHandler), 
    (r'/corpus/tags', TagsHandler),
])

if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()