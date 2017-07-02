#!/usr/bin/env python3
"""
This file is a part of "make-a-search-engine-from-empty-code"
MIT License Copyright (c) 2017 thisLight 
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
"""
import re
import datetime
import requests as reqs
import pymongo as mongo
from bs4 import BeautifulSoup


# Regex from https://daringfireball.net/2010/07/improved_regex_for_matching_urls
PATTERN = re.compile(r"(?i)\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'\".,<>?«»“”‘’]))")


class WalkerException(Exception):
    pass


class GetDocumentException(WalkerException):
    def __init__(self, uri, status_code):
        self.uri = uri
        self.status_code = status_code
    
    def __str__(self):
        return "GetDocumentException: status {code} on {uri}".format(
            code=self.status_code,
            uri=self.uri
        )


def get_all_uri(string) -> str:
    for x in PATTERN.finditer(string):
        yield x.group(0)


class WebDocument(object):
    def __init__(self, string, origin=None):
        self.string = string
        self.origin = origin
        self.soup = BeautifulSoup(string, "html5lib")
    
    def get_uris(self) -> str:
        yield from get_all_uri(self.string)

    @property
    def title(self):
        return self.soup.title.string
    
    @property
    def text(self):
        return self.soup.get_text()
    
    @classmethod
    def from_url(cls, url):
        if "://" not in url:
            url = "http://"+url
        res = reqs.get(url)
        if res.ok and (res.status_code == 200):
            return cls(res.text, origin=url)
        else:
            print(
                "{url} is not ok, status code {code}".format(
                    url=url,
                    code=res.status_code
                    )
                )
            # raise GetDocumentException(url, res.status_code)


class Walker(object):
    def __init__(self, dbclient, start="https://pondof.fish"):
        self.dbclient = dbclient
        self._init_env()
        self.add_uri(start)
    
    def _init_env(self):
        self.uri_list = []
        self.db = self.dbclient.searchEngine.pages
    
    def add_uri(self, uri):
        if not (uri in self.uri_list):
            self.uri_list.append(uri)
            print(
                "Walker: '{uri}' has been added to waiting list, waiting list has {ln} URIs.".format(
                    uri=uri,
                    ln=len(self.uri_list)
                    )
                )
    
    def insert_body(self, doc, time=None):
        """Insert document to database
        
        struct:
        {
            title:str,
            url:str,
            text:str,
            source:str,
            last_update:int(c format),
        }
        """
        if not time:
            time = datetime.datetime.now().ctime()
        post = {"$set": {
            "title": doc.title,
            "url": doc.origin,
            "text": doc.text,
            "source": doc.string,
            "last_update": time
            }
        }
        self.db.update_one({"url": doc.origin}, post, upsert=True)
    
    def get_uri(self):
        print("Walker: URIs list dump: {}".format(repr(self.uri_list)))
        return self.uri_list.pop()
    
    def do_next(self):
        uri = self.get_uri()
        try:
            print("Walker: Get {}".format(uri))
            doc = WebDocument.from_url(uri)
            if not doc:
                return
            for uri in doc.get_uris():
                print("Walker: got {uri} from page".format(uri=uri))
                self.add_uri(uri)
            self.insert_body(doc)
        except GetDocumentException as e:
            print(e)

    
    def loop(self):
        while True:
            print("Walker: enter a new loop step")
            self.do_next()


def main():
    Walker(mongo.MongoClient()).loop()

 
def __main__():
    main()


if __name__ == "__main__":
    main()
