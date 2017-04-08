import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.autograd import Variable

class SearchTask(nn.Module):
    def __init__(self, state_dim, n_actions, reference, **kwargs):
        # initialize the pytorch module
        super(SearchTask, self).__init__()

        # remember reference
        self._lts_reference = reference

        # set up cost sensitive one-against-all
        # TODO make this generalizable
        self._lts_csoaa_predict = nn.Linear(state_dim, n_actions)
        self._lts_loss_fn = torch.nn.MSELoss(size_average=False) # only sum, don't average

        # set up options
        self._lts_autoref = kwargs.get('autoref', False)
        self._lts_warning = kwargs.get('warning', 'none')
        assert self._lts_warning in ['none', 'short', 'long', 'stop'], 'warning must be one of none, short, long, stop'

    def act(self, state, a_ref=None):
        if not self.training:
            # we're in test mode, just act greedily
            return self.act_greedy(state)
        
        # otherwise, we're training, so we need to ask the lts_method
        # how we should act. first, ensure that we have a reference
        # action, either as an argument, or via autoref. if both are
        # on, then a_ref overrides the action (but a warning is
        # issued).
        if a_ref is None:
            if not self._lts_autoref:
                raise Exception('during training mode, SearchTask.act was called but no reference action was given (and autoref is False)')
            else:
                a_ref = self.ref_policy.next()
        elif self._lts_autoref:
            self._warn('SearchTask has autoref=True but act() was called with a reference action anyway; defaulting to argument and ignoring autoref')

        # get the action selected by the method
        a = self._lts_method.act(state, a_ref)

        # execute that action
        return self._execute_action(a)

    def act_greedy(self, state):
        # predict costs using the csoaa model
        pred_costs = self._lts_csoaa_predict(state)
        # return the argmin cost
        return pred_costs.argmin()

    def act_sample(self, state):
        # predict costs using csoaa model
        pred_costs = self._lts_csoaa_predict(state)
        # return a soft-min sample (==softmax on negative costs)
        return F.softmax(-pred_costs).multinomial()

    def lts_objective(self, state, truth):
        # truth must be one of:
        #  - None: ignored
        #  - an int specifying the single true output (which gets cost zero, rest are cost one)
        #  - a list of ints specifying multiple true outputs (ala above)
        #  - a 1d torch tensor specifying the exact costs of every action
        if truth is None:
            return 0.
        
        pred_costs = self._lts_csoaa_predict(state)

        if isinstance(truth, int): truth = [truth]
        if isinstance(truth, list):
            truth0 = truth
            truth = torch.ones(pred_costs.size())
            for k in truth0:
                truth[0,k] = 0.
        if isinstance(truth, torch.FloatTensor):
            truth = Variable(truth, requires_grad=False)
            return self._lts_loss_fn(pred_costs, truth)

        raise Exception('lts_objective got truth of invalid type (%s) expecting int, list[int] or torch.FloatTensor' % str(type(truth)))

    def forward(self, input, truth=None, lts_method=None):
        # if we're running in test mode, that's easy
        if truth is None or lts_method is None:
            self.training = False
            return self._run(input)

        # otherwise, we're training, which means that lts_method needs
        # to be in charge
        self.training = True

        # construct the reference policy
        self.ref_policy = self._lts_reference(truth) if self.training else None

        # to act() we need the lts_method to tell us what to do
        self._lts_method = lts_method

        # start training
        self.last_loss = lts_method.train(self, input)

    def _execute_action(self, a):
        # a is either an action (int) or list of actions
        if isinstance(a, int):
            pass
        elif isinstance(a, list):
            if len(a) == 0:
                self._warn('empty list of actions in _execute_action; defaulting to 0')
                a = 0
            else:
                a = a[0]
        elif a is None:
            self._warn('_execute_action called with a=None; defaulting to 0')
            a = 0
        else:
            raise Exception('_execute_action called on non int/list (%s)' % str(type(a)))

        # if we're doing autoref, we need to tell ref about this action
        self.ref_policy.step(a)

        return a
    
    def _warn(self, warning):
        if self._lts_warning == 'stop':
            raise Exception(warning)
        
        if self._lts_warning == 'none':
            return
        
        print >>sys.stderr, 'warning: %s' % warning
        if self._lts_warning != 'long':
            traceback.print_stack(file=sys.stderr)
            print >>sys.stderr, ''
            
