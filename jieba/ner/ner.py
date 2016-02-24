# -*- coding: utf-8 -*-
import codecs

def load_train_file(train_file):
    f = codecs.open(train_file, "r")
    for line in f.readlines():
        for item in line[22:].decode("gbk").strip().split():
            word, tag = item.split('/')
            if word[0] == '[':
                print word, tag

            elif tag.find(']') >= 0:
                print word, tag
            else:
                word, tag
if __name__ == "__main__":
    load_train_file("./199801.txt")