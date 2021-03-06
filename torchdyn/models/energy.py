import torch
import torch.nn as nn
from torch.autograd.functional import jacobian, hessian 
from functools import partial

class Stable(nn.Module):
    """Stable Neural ODE

    :param func: function parametrizing the vector field.
    :type func: nn.Module
    """
    def __init__(self, net:nn.Module):
        super().__init__()
        self.net = net

    def forward(self, x):
        with torch.set_grad_enabled(True):
            bs, n = x.shape[0], x.shape[1] // 2
            x = x.requires_grad_(True)
            eps = self.net(x).sum()
            out = -torch.autograd.grad(eps, x, allow_unused=False, create_graph=True)[0] 
        return out

class HNN(nn.Module):
    """Hamiltonian Neural ODE

    :param net: function parametrizing the vector field.
    :type net: nn.Module
    """
    def __init__(self, net:nn.Module):
        super().__init__()
        self.net = net

    def forward(self, x):
        x.requires_grad_(True) ; n = x.shape[1] // 2
        gradH = torch.autograd.grad(self.net(x).sum(), x,
                                    create_graph=True)[0]
        return torch.cat([gradH[:, n:], -gradH[:, :n]], 1).to(x)

    
class LNN(nn.Module):
    """Lagrangian Neural ODE

    :param net: function parametrizing the vector field.
    :type net: nn.Module
    """
    def __init__(self, net):
        super().__init__()
        self.net = net
        
    def forward(self, x):
        self.n = n = x.shape[1]//2 ; bs = x.shape[0]   
        x = torch.autograd.Variable(x, requires_grad=True)
        qqd_batch = tuple(x[i, :] for i in range(bs))
        jac = tuple(map(partial(jacobian, self._lagrangian, create_graph=True), qqd_batch))
        hess = tuple(map(partial(hessian, self._lagrangian, create_graph=True), qqd_batch))
        qdd_batch = tuple(map(self._qdd, zip(jac, hess, qqd_batch)))
        qd, qdd = x[:, n:], torch.cat([qdd[None] for qdd in qdd_batch])
        return torch.cat([qd, qdd], 1)
    
    def _lagrangian(self, qqd):
        return self.net(qqd).sum()
    
    def _qdd(self, inp):
        n = self.n ; jac, hess, qqd = inp
        return hess[n:, n:].pinverse()@(jac[:n] - hess[n:, :n]@qqd[n:])
    
    
