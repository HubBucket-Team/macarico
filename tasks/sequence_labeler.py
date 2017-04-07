import torch
import torch.nn as nn
from torch.autograd import Variable
import macarico

class SequenceLabeler(macarico.SearchTask):
    def __init__(self, n_words, n_labels, ref_policy, **kwargs):
        # we need to know the size of the hidden state
        n_hid    = kwargs.get('n_hid',    50)
        n_emb    = kwargs.get('n_emb',    n_hid)
        n_layers = kwargs.get('n_layers', 1)
        
        # initialize the parent class; this needs to know the
        # branching factor of the task (in this case, the branching
        # factor is exactly the number of labels), the dimensionality
        # of the thing that will be used to make that prediction, and
        # the reference policy
        super(SequenceLabeler, self).__init__(n_hid, n_labels, ref_policy)

        # set up simple sequence labeling model, which runs an LSTM
        # _backwards_ over the input, and then predicts left-to-right
        self.encoder = nn.Embedding( n_words, n_emb )
        self.rnn     = nn.LSTM(n_emb, n_hid, n_layers, dropout=kwargs.get('dropout', 0.5))

    def _run(self, words):
        N = len(words)
        
        # first, run the LSTM backwords over (embeddings of) words
        embeddings = self.encoder(words)
        _,hiddens  = self.rnn(embeddings, self._init_hidden())
        
        # second, make predictions left-to-right
        output = []
        for n in range(N):
            # extract the neural state on which we will make a
            # prediction; since the sentence was encoded backwards, we
            # read this from the end
            state = hiddens[N-n-1]
            
            # choose an action by calling self.act; this is defined
            # for you by macarico.SearchTask
            a = self.act(state)

            # append output
            output.append(a)

        return output

    def _init_hidden(self):
        return Variable(torch.zeros(1, 1, self.n_hid))

# test usage:

task = SequenceLabeler(n_words,
                       n_labels,
                       macarico.HammingReference,
                      )                       
 
lts_method = macarico.MaximumLikelihood()

optimizer  = ag.SGD(...)

# train
for words,labels in training_data:
    task.forward(words, labels, lts_method)
    task.backward()
    optimizer.step()

# test
for words,labels in test_data:
    pred = task.forward(words)  # no labels ==> test mode
    print 'truth = {labels}\npred  = {pred}\n' % dict(labels=labels, pred=pred)


