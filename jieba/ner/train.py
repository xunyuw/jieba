# encoding=utf-8
import pprint
import math
import sys
import pickle
import codecs
import os
import jieba
import jieba.posseg as pseg

# for 199801.txt
def relabeled_tag(train_file, output_file, pattern_file):
    f_out = codecs.open(output_file, 'w', 'utf8')
    f_pattern = codecs.open(pattern_file, 'w', 'utf8')
    existed_pattern = []

    with codecs.open(train_file, 'r') as f:
        for line in f.readlines():

            line = line.decode('gbk')
            # if line.find(']nt') < 0:
            #     continue

            nt_list = []
            start_pos = 0
            words = line.split()
            for index, item in enumerate(words):
                if index == 0:
                    continue
                word, tag = item.split('/')
                if word[0] == '[':
                    start_pos = index
                if tag.find("]") >= 0:
                    if tag[-2:] == 'nt':
                        nt_list.append((start_pos, index + 1))
                    else:
                        start_pos = 0

            cleaned_sent = []
            cleaned_sent.append('__START__/#')
            for index, item in enumerate(words):
                if index == 0:
                    continue
                if item[0] == '[':
                    item = item[1:]

                cleaned_sent.append(item)
            cleaned_sent.append('__END__/#')
            # print cleaned_sent

            for nt_tuple in nt_list:

                # tag precious
                tmp_word, tmp_tag = cleaned_sent[nt_tuple[0] - 1].split('/')
                if tmp_tag == 'B':
                    tmp_tag = 'X'
                else:
                    tmp_tag = 'A'
                cleaned_sent[nt_tuple[0] - 1] = tmp_word + '/' + tmp_tag

                # tag next
                tmp_word, tmp_tag = cleaned_sent[nt_tuple[1]].split('/')
                tmp_tag = 'B'
                cleaned_sent[nt_tuple[1]] = tmp_word + '/' + tmp_tag


                # tag inside
                tmp_pattern = ''
                for index, word in enumerate(words[nt_tuple[0]: nt_tuple[1]]):
                    tmp_word, tmp_tag = word.split('/')

                    if tmp_word[0] == '[':
                        tmp_word = tmp_word[1:]
                    if tmp_tag[-3:] == ']nt':
                        tmp_tag = tmp_tag[:-3]

                    if tmp_tag == 'ns':
                        tmp_word = '__PLACE__'
                        tmp_tag = 'G'
                    elif tmp_tag == 'nt':
                        tmp_word = '__ORG__'
                        tmp_tag = 'K'
                    elif tmp_tag == 'nr':
                        tmp_word = '__NAME__'
                        tmp_tag = 'N'
                    elif tmp_tag == 'n':
                        tmp_tag = 'C'
                    elif tmp_tag == 'nz':
                        tmp_tag = 'F'
                    elif tmp_tag == 'j':
                        tmp_tag = 'J'
                    elif tmp_tag == 'vn':
                        tmp_tag = 'C'
                    elif tmp_tag == 'w':
                        tmp_tag = 'W'
                    elif tmp_tag == 'f':
                        tmp_tag = 'Y'
                    elif tmp_tag == 'v':
                        tmp_tag = 'C'
                    elif tmp_tag == 'x':
                        tmp_tag = 'L'
                    else:
                        tmp_tag = 'C'

                    if index == len(words[nt_tuple[0]: nt_tuple[1]]) - 1:
                        tmp_tag = 'D'
                    # print tmp_word, tmp_tag
                    tmp_pattern += tmp_tag
                    cleaned_sent[nt_tuple[0] + index] = tmp_word + '/' + tmp_tag
                if tmp_pattern not in existed_pattern:
                    existed_pattern.append(tmp_pattern)

            for index, item in enumerate(cleaned_sent):
                tmp_word, tmp_tag = item.rsplit('/', 1)
                if tmp_tag == 'nt':
                    cleaned_sent[index] = tmp_word + '/' + 'K'

                    pre_word, pre_tag = cleaned_sent[index - 1].split('/')
                    if pre_tag == 'B':
                        cleaned_sent[index - 1] = pre_word + '/' + 'X'
                    else:
                        cleaned_sent[index - 1] = pre_word + '/' + 'A'
                    next_word, next_tag = cleaned_sent[index + 1].split('/')
                    if pre_tag == 'A':
                        cleaned_sent[index + 1] = next_word + '/' + 'X'
                    else:
                        cleaned_sent[index + 1] = next_word + '/' + 'B'
                elif tmp_tag != tmp_tag.upper():
                    cleaned_sent[index] = tmp_word + '/' + 'Z'
            f_out.write(' '.join(cleaned_sent) + '\n')
    f_pattern.write('\n'.join(existed_pattern))
    f_out.close()
    f_pattern.close()

# for labeled train file and company file
def train_model(train_file):
    segged_file = open(train_file, 'r')
    prob_emit = {}
    prob_trans = {}
    char_state_tab = {}

    # Normal labeled file
    for count, line in enumerate(segged_file.readlines()):
        print count
        pre_word = ''
        pre_tag = ''

        line = line.strip()

        for item in line.split():
            word, tag = item.rsplit('/', 1)

            word = word.decode('utf8')

            # prob_emit generate

            if tag in prob_emit.keys():
                try:
                    prob_emit[tag][word] += 1
                except:
                    prob_emit[tag][word] = 1
            else:
                prob_emit[tag] = {}
                prob_emit[tag][word] = 1

            # prob_trans generate
            if pre_word and pre_tag:
                if pre_tag in prob_trans.keys():
                    try:
                        prob_trans[pre_tag][tag] += 1
                    except:
                        prob_trans[pre_tag][tag] = 1
                else:
                    prob_trans[pre_tag] = {}
                    prob_trans[pre_tag][tag] = 1
            pre_word = word
            pre_tag = tag

        # prob_trans last char generate
        if pre_tag and pre_word:
            if pre_tag in prob_trans.keys():
                try:
                    prob_trans[pre_tag][tag] += 1
                except:
                    prob_trans[pre_tag][tag] = 1
            else:
                prob_trans[pre_tag] = {}
                prob_trans[pre_tag][tag] = 1

    # prob_start and char_state_tab generate
    prob_start = {}
    for key in prob_emit.keys():
        for item in prob_emit[key]:
            # prob_start generate
            try:
                prob_start[key] += prob_emit[key][item]
            except:
                prob_start[key] = prob_emit[key][item]

            # char_state_tab generate
            if item in char_state_tab.keys():
                if key not in char_state_tab[item]:
                    char_state_tab[item] = (key,) + char_state_tab[item]
            else:
                char_state_tab[item] = ()
                char_state_tab[item] = (key,) + char_state_tab[item]

    # normalization
    for key in prob_emit:
        total = 0.0
        for item in prob_emit[key]:
            total += float(prob_emit[key][item])
        for item in prob_emit[key]:
            if float(prob_emit[key][item]) == 0.0:
                prob_emit[key][item] = math.log(sys.float_info.min)
            else:
                prob_emit[key][item] = math.log(float(prob_emit[key][item]) / total)

    for key in prob_trans:
        total = 0.0
        for item in prob_trans[key]:
            total += float(prob_trans[key][item])
        for item in prob_trans[key]:
            if float(prob_trans[key][item]) == 0.0:
                prob_trans[key][item] = math.log(sys.float_info.min)
            else:
                prob_trans[key][item] = math.log(float(prob_trans[key][item]) / total)

    total = 0.0
    for key in prob_start:
        total += float(prob_start[key])
    for key in prob_start:
        if float(prob_start[key]) == 0.0:
            prob_start[key] = math.log(sys.float_info.min)
        else:
            prob_start[key] = math.log(float(prob_start[key]) / total)

    f = open('./char_state_tab.pkl', 'wb')
    pickle.dump(char_state_tab, f)
    f.close()

    f = open('./prob_emit.pkl', 'wb')
    pickle.dump(prob_emit, f)
    f.close()

    f = open('./prob_start.pkl', 'wb')
    pickle.dump(prob_start, f)
    f.close()

    f = open('./prob_trans.pkl', 'wb')
    pickle.dump(prob_trans, f)
    f.close()

    pprint.pprint(prob_emit)
    # pprint.pprint(char_state_tab)
    segged_file.close()


def label_sents(tag_type, existed_pattern, segged_dict, line):

    segged_words = pseg.cut(line.strip())


    cleaned_sent = []
    cleaned_sent.append('__START__/#')
    pre_word = ''
    pre_tag = ''
    for index, word in enumerate(segged_words):
        if word.flag == tag_type:

            #previous word
            tmp_word, tmp_tag = cleaned_sent[index].rsplit('/', 1)
            if tmp_tag == 'B':
                tmp_tag = 'X'
            else:
                tmp_tag = 'A'
            cleaned_sent[index] = tmp_word + '/' + tmp_tag

            if word.word in segged_dict.keys():
                words_in_dict = segged_dict[word.word].split()
                tmp_pattern = ''
                for index_in_dict, word_in_dict in enumerate(words_in_dict):
                    tmp_word, tmp_tag = word_in_dict.rsplit('/', 1)

                    if tmp_tag == 'ns':
                        tmp_word = '__PLACE__'
                        tmp_tag = 'G'
                    elif tmp_tag == 'nt':
                        tmp_word = '__ORG__'
                        tmp_tag = 'K'
                    elif tmp_tag == 'nr':
                        tmp_word = '__NAME__'
                        tmp_tag = 'N'
                    elif tmp_tag == 'n':
                        tmp_tag = 'C'
                    elif tmp_tag == 'nz':
                        tmp_tag = 'F'
                    elif tmp_tag == 'j':
                        tmp_tag = 'J'
                    elif tmp_tag == 'vn':
                        tmp_tag = 'C'
                    elif tmp_tag == 'w':
                        tmp_tag = 'W'
                    elif tmp_tag == 'f':
                        tmp_tag = 'Y'
                    elif tmp_tag == 'v':
                        tmp_tag = 'C'
                    elif tmp_tag == 'x':
                        tmp_tag = 'L'
                    else:
                        tmp_tag = 'C'

                    if len(words_in_dict) == index_in_dict+1:
                        tmp_tag = 'D'

                    cleaned_sent.append(tmp_word + '/' + tmp_tag)
                    tmp_pattern += tmp_tag

                if tmp_pattern not in existed_pattern:
                    existed_pattern.append(tmp_pattern)
            else:

                if word.flag == 'ns':
                    tmp_word = '__PLACE__'
                    tmp_tag = 'G'
                elif word.flag == 'nt':
                    tmp_word = '__ORG__'
                    tmp_tag = 'K'
                elif word.flag == 'nr':
                    tmp_word = '__NAME__'
                    tmp_tag = 'N'
                else:
                    tmp_word = word.word
                    tmp_tag = 'D'

                cleaned_sent.append(tmp_word + '/' + tmp_tag)

        else:
            if pre_tag == 'D':
                tmp_word = word.word
                tmp_tag = 'B'
                cleaned_sent.append(tmp_word + '/' + tmp_tag)
            else:
                tmp_word = word.word
                tmp_tag = 'Z'
                cleaned_sent.append(tmp_word + '/' + tmp_tag)
        pre_word = tmp_word
        pre_tag = tmp_tag
    cleaned_sent.append('__END__/#')
    # print cleaned_sent

    return ' '.join(cleaned_sent)


def train_model_from_raw(tag_type, raw_file, dictionary, pattern_file):

    segged_dict = {}
    prob_emit = {}
    prob_trans = {}
    f_pattern = codecs.open(pattern_file, 'w', 'utf8')
    existed_pattern = []

    with codecs.open(dictionary, 'r', 'utf8') as f:
        for line in f.readlines():
            label_line = []
            ori_word = line.strip()
            if len(ori_word) >= 3:
                segged_words = pseg.cut(ori_word)

                cleaned_words = []
                for index, word in enumerate(segged_words):
                    if index == 0 and (word.flag == 'nr' or word.flag == 'nrfg'):
                        break
                    cleaned_words.append(word.word+'/'+word.flag)
                if cleaned_words:
                    segged_dict[ori_word] = ' '.join(cleaned_words)
                    # print segged_dict[ori_word]

    for key in segged_dict.keys():
        jieba.add_word(key, tag=tag_type)


    with codecs.open(raw_file, 'r', 'utf8') as f:
        for index, line in enumerate(f.readlines()):

            labeled_line = label_sents(tag_type, existed_pattern, segged_dict, line.strip())

            pre_word = ''
            pre_tag = ''


            for item in labeled_line.split():
                word, tag = item.rsplit('/', 1)

                # prob_emit generate

                if tag in prob_emit.keys():
                    try:
                        prob_emit[tag][word] += 1
                    except:
                        prob_emit[tag][word] = 1
                else:
                    prob_emit[tag] = {}
                    prob_emit[tag][word] = 1

                # prob_trans generate
                if pre_word and pre_tag:
                    if pre_tag in prob_trans.keys():
                        try:
                            prob_trans[pre_tag][tag] += 1
                        except:
                            prob_trans[pre_tag][tag] = 1
                    else:
                        prob_trans[pre_tag] = {}
                        prob_trans[pre_tag][tag] = 1
                pre_word = word
                pre_tag = tag

            # prob_trans last char generate
            if pre_tag and pre_word:
                if pre_tag in prob_trans.keys():
                    try:
                        prob_trans[pre_tag][tag] += 1
                    except:
                        prob_trans[pre_tag][tag] = 1
                else:
                    prob_trans[pre_tag] = {}
                    prob_trans[pre_tag][tag] = 1

    # prob_start and char_state_tab generate
    prob_start = {}
    char_state_tab = {}
    for key in prob_emit.keys():
        for item in prob_emit[key]:
            # prob_start generate
            try:
                prob_start[key] += prob_emit[key][item]
            except:
                prob_start[key] = prob_emit[key][item]

            # char_state_tab generate
            if item in char_state_tab.keys():
                if key not in char_state_tab[item]:
                    char_state_tab[item] = (key,) + char_state_tab[item]
            else:
                char_state_tab[item] = ()
                char_state_tab[item] = (key,) + char_state_tab[item]

    # normalization
    for key in prob_emit:
        total = 0.0
        for item in prob_emit[key]:
            total += float(prob_emit[key][item])
        for item in prob_emit[key]:
            if float(prob_emit[key][item]) == 0.0:
                prob_emit[key][item] = math.log(sys.float_info.min)
            else:
                prob_emit[key][item] = math.log(float(prob_emit[key][item]) / total)


    for key in prob_trans:
        total = 0.0
        for item in prob_trans[key]:
            total += float(prob_trans[key][item])
        for item in prob_trans[key]:
            if float(prob_trans[key][item]) == 0.0:
                prob_trans[key][item] = math.log(sys.float_info.min)
            else:
                prob_trans[key][item] = math.log(float(prob_trans[key][item]) / total)


    total = 0.0
    for key in prob_start:
        total += float(prob_start[key])
    for key in prob_start:
        if float(prob_start[key]) == 0.0:
            prob_start[key] = math.log(sys.float_info.min)
        else:
            prob_start[key] = math.log(float(prob_start[key]) / total)

    f = open('./char_state_tab.pkl', 'wb')
    pickle.dump(char_state_tab, f)
    f.close()

    f = open('./prob_emit.pkl', 'wb')
    pickle.dump(prob_emit, f)
    f.close()

    f = open('./prob_start.pkl', 'wb')
    pickle.dump(prob_start, f)
    f.close()

    f = open('./prob_trans.pkl', 'wb')
    pickle.dump(prob_trans, f)
    f.close()

    f_pattern.write('\n'.join(existed_pattern))
    f_pattern.close()
    # pprint.pprint(prob_emit)
    # pprint.pprint(char_state_tab)

    # line_list = []
    # f_out = codecs.open('nt.add_dict.txt', 'w', 'utf8')
    # with codecs.open('source.txt', 'r', 'utf8') as f:
    #     for index, line in enumerate(f.readlines()):
    #         is_add = False
    #         words = pseg.cut(line.strip())
    #         for word in words:
    #             if word.flag == 'organization':
    #                 if not is_add:
    #                     f_out.write(line.strip() + '\n')
    #                     is_add = True
    #                     line_list.append(str(index))
    #                 print word.word, word.flag
    # f_out.close()
    #
    # f = open('line.txt', 'w')
    # f.write(','.join(line_list))
    # f.close()

    # f = open('line.txt')
    # line_list = f.read().split(',')
    # f.close()
    #
    # f_out = codecs.open('nt.raw.txt', 'w', 'utf8')
    # with codecs.open('source.txt', 'r', 'utf8') as f:
    #     for index, line in enumerate(f.readlines()):
    #         is_add = False
    #         if str(index) in line_list:
    #             is_add = True
    #             words = pseg.cut(line.strip())
    #             for word in words:
    #                 f_out.write(word.word + '/' + word.flag + ' ')
    #         if is_add:
    #             f_out.write('\n')
    # f_out.close()

    # with codecs.open('OrginizationName.txt', 'r', 'utf8') as f:
    #     for index, line in enumerate(f.readlines()):
    #         word = line.split()[0]
    #         if len(word) >= 3:
    #             jieba.add_word(word, tag='organization')

    #
    # f_dict = codecs.open('nt.add_dict.txt', 'r', 'utf8')
    # f_raw = codecs.open('nt.raw.txt', 'r', 'utf8')
    #
    # dict_lines = f_dict.readlines()
    # raw_lines = f_raw.readlines()
    #
    # f_dict.close()
    # f_raw.close()
    #
    # for index, line in enumerate(dict_lines):
    #     raw_sentence = raw_lines[index]
    #     raw_list = raw_sentence.split()
    #     print ' '.join(raw_list)
    #     words = pseg.cut(line.strip())
    #     for word in words:
    #         print word.word + '/' + word.flag,
    #     print ''
    #


if __name__ == '__main__':
    # f_out = codecs.open(raw_file, 'w', 'utf8')
    # for root, directories, files in os.walk('./tagged'):
    #     for filename in files:
    #         f = codecs.open(os.path.join(root, filename), 'r')
    #         for line in f.readlines():
    #             out_line = ''.join(line.decode('utf8').strip().split())
    #             f_out.write(out_line)
    #
    #             if out_line and (out_line[-1] == u'。' or out_line[-1] == u'？' or out_line[-1] == u'！' or out_line[-1] == u'；'):
    #                 f_out.write('\n')
    #         f.close()
    # f_out.close()

    train_model_from_raw('ognization', "./source.txt", u'./公司名.txt', './pattern.txt')
    # train_model()
    # relabeled_tag(u'./199801.txt', './labeled.txt', './pattern.txt')
    # train_model('./labeled.txt')


