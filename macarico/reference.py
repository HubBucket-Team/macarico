import torch
import torch.nn as nn
from torch.autograd import Variable

class Reference:
    def __init__(self, truth=None):
        pass

    def reset(self):
        raise Exception('reset not defined')

    def step(self, p):
        raise Exception('step not defined')
    
    def loss(self):
        raise Exception('loss not defined')
    
    def next(self):
        raise Exception('next not defined')


class HammingReference(Reference):
    def __init__(self, truth=None):
        self.truth = truth
        self.reset()
        
    def reset(self):
        self.prediction = []

    def step(self, a):
        self.prediction.append(a)

    def loss(self):
        loss = 0.
        for n,y in enumerate(self.truth):
            if n >= len(self.prediction) or y != prediction[n]:
                loss += 1.
        loss += max(0., len(prediction) - len(self.truth))
        return loss

    def next(self):
        n = len(self.prediction)
        if n >= len(self.truth):
            return 0
        return self.truth[n]


    
