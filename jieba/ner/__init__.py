#encoding=utf-8
from __future__ import absolute_import, unicode_literals
import re
import os
import sys
import pickle


MIN_FLOAT = -3.14e100
MIN_INF = float("-inf")

PROB_START_P = "./prob_start.pkl"
PROB_TRANS_P = "./prob_trans.pkl"
PROB_EMIT_P = "./prob_emit.pkl"
CHAR_STATE_TAB_P = "./char_state_tab.pkl"


def load_model():
    start_p = pickle.load(open(PROB_START_P))
    trans_p = pickle.load(open(PROB_TRANS_P))
    emit_p = pickle.load(open(PROB_EMIT_P))
    state = pickle.load(open(CHAR_STATE_TAB_P))
    return state, start_p, trans_p, emit_p

state_P, start_P, trans_P, emit_P = load_model()


def viterbi(obs, states, start_p, trans_p, emit_p):
    V = [{}]  # tabular
    mem_path = [{}]
    all_states = trans_p.keys()
    for y in states.get(obs[0], all_states):  # init
        V[0][y] = start_p[y] + emit_p[y].get(obs[0], MIN_FLOAT)
        mem_path[0][y] = ''
    for t in xrange(1, len(obs)):
        V.append({})
        mem_path.append({})
        #prev_states = get_top_states(V[t-1])
        prev_states = [
            x for x in mem_path[t - 1].keys() if len(trans_p[x]) > 0]

        prev_states_expect_next = set(
            (y for x in prev_states for y in trans_p[x].keys()))
        obs_states = set(
            states.get(obs[t], all_states)) & prev_states_expect_next

        if not obs_states:
            obs_states = prev_states_expect_next if prev_states_expect_next else all_states

        for y in obs_states:
            prob, state = max((V[t - 1][y0] + trans_p[y0].get(y, MIN_INF) +
                               emit_p[y].get(obs[t], MIN_FLOAT), y0) for y0 in prev_states)
            V[t][y] = prob
            mem_path[t][y] = state

    last = [(V[-1][y], y) for y in mem_path[-1].keys()]
    # if len(last)==0:
    #     print obs
    prob, state = max(last)

    route = [None] * len(obs)
    i = len(obs) - 1
    while i >= 0:
        route[i] = state
        state = mem_path[i][state]
        i -= 1
    return (prob, route)


def find_all(a_str, sub):
    start = 0
    while True:
        start = a_str.find(sub, start)
        if start == -1: return
        yield start
        start += 1 # use start += 1 to find overlapping matches

if __name__ == "__main__":
    import codecs
    import jieba
    import jieba.posseg as pseg
    import re
    import math
    from jieba.ner.pyAhocorasick import Ahocorasick
    states, start_p, trans_p, emit_p = load_model()
    # words = pseg.cut(u'2013年8月，任民政部党组成员、优抚安置局局长、全国退役士兵安置工作领导小组办公室副主任。')
    # words = pseg.cut(u'清晨5点他就起床，将写好的辞职信看了又看，放在随身的公文包里，然后将领带重新系了系，他要向工作了15年的陕西省高级人民法院递交这封辞职信，正式向组织提出辞去公职。')
    # # print ' '.join([word.word + '/' + word.flag for word in words])
    # sentence = ['__START__']
    # for word in words:
    #     if word.flag == 'ns':
    #         sentence.append('__PLACE__')
    #     elif word.flag == 'nt':
    #         sentence.append('__ORG__')
    #     elif word.flag == 'nr':
    #         sentence.append('__NAME__')
    #     else:
    #         sentence.append(word.word)
    # sentence += ['__END__']
    # print ' '.join(sentence)
    # print viterbi(sentence, states, start_p, trans_p, emit_p)
    ah = Ahocorasick()
    f_out = codecs.open('result.txt', 'w', 'utf8')
    patterns = []
    for line in open('pattern.txt', 'r').readlines():
        patterns.append(line.strip())
        ah.addWord(line.strip())
        print line.strip()
    ah.make()

    # for key in start_p:
    #     if start_p[key] == 0.0:
    #         start_p[key] = math.log(sys.float_info.min)
    #
    # for key in trans_p:
    #     for key1 in trans_p[key]:
    #         if trans_p[key][key1] == 0.0:
    #             trans_p[key][key1] = math.log(sys.float_info.min)
    #
    # for key in emit_p:
    #     for key1 in emit_p[key]:
    #         if emit_p[key][key1] == 0.0:
    #             emit_p[key][key1] = math.log(sys.float_info.min)

    word_label = {}
    f = codecs.open('matrix.txt', 'w', 'utf8')
    for key in emit_p:
        f.write(key + '\n')
        for key1 in emit_p[key]:
            try:
                word_label[key1].append((key, emit_p[key][key1]))
            except:
                word_label[key1] = []
                word_label[key1].append((key, emit_p[key][key1]))
            f.write('\t' + key1 + ':' + str(emit_p[key][key1]) + '\n')
    f.close()


    with open('人民日报半年语料库.txt', 'r') as f:
        for line in f.readlines():
            tmp_line = ''
            for word in line.decode('gbk').strip().split():
                word = word.split('/')[0]
                tmp_line += word
            words = pseg.cut(tmp_line)
            # print ' '.join([word.word + '/' + word.flag for word in words])
            sentence = ['__START__']

            cut_words = []
            for word in words:
                cut_words.append(word.word+'/'+word.flag)
                if word.flag == 'ns':
                    sentence.append('__PLACE__')
                elif word.flag == 'nt':
                    sentence.append('__ORG__')
                elif word.flag == 'nr':
                    sentence.append('__NAME__')
                else:
                    sentence.append(word.word)
            sentence += ['__END__']

            label = viterbi(sentence, states, start_p, trans_p, emit_p)
            label_str = ''.join(label[1])

            for item in ah.search(label_str):
                # print item
                print ' '.join(cut_words)
                print label_str
                # print label[1]
                for i in xrange(item[0], item[1]+1):

                    print sentence[i],
                    print label[1][i],
                    try:
                        print word_label[sentence[i]],
                    except:
                        print 'unknown',
                print ''

            # print label_str
            # for pattern in patterns:
            #
            #     find_pattern = list(find_all(label_str, pattern))
            #     if find_pattern:
            #         print find_pattern

                # if(string.find(label_str,pattern)!=-1):
                #     print pattern

            labeled_sents = ''
            for index, item in enumerate(sentence):
                labeled_sents += item + '/' + label[1][index] + ' '
            # print labeled_sents

            f_out.write(labeled_sents + '\n')
    f_out.close()