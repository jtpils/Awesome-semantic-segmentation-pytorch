"""Custom losses."""
import torch
import torch.nn as nn

from torch.autograd import Variable

__all__ = ['MixSoftmaxCrossEntropyLoss', 'EncNetLoss']


class MixSoftmaxCrossEntropyLoss(nn.CrossEntropyLoss):
    def __init__(self, aux=True, aux_weight=0.2, ignore_label=-1, **kwargs):
        super(MixSoftmaxCrossEntropyLoss, self).__init__(ignore_index=ignore_label)
        self.aux = aux
        self.aux_weight = aux_weight

    def _aux_forward(self, *inputs, **kwargs):
        *preds, target = tuple(inputs)

        loss = super(MixSoftmaxCrossEntropyLoss, self).forward(preds[0], target)
        for i in range(1, len(preds)):
            aux_loss = super(MixSoftmaxCrossEntropyLoss, self).forward(preds[i], target)
            loss += self.aux_weight * aux_loss
        return loss

    def forward(self, *inputs, **kwargs):
        preds, target = tuple(inputs)
        inputs = tuple(list(preds) + [target])
        if self.aux:
            return self._aux_forward(*inputs)
        else:
            return super(MixSoftmaxCrossEntropyLoss, self).forward(*inputs)


# reference: https://github.com/zhanghang1989/PyTorch-Encoding/blob/master/encoding/nn/loss.py
class EncNetLoss(nn.CrossEntropyLoss):
    """2D Cross Entropy Loss with SE Loss"""

    def __init__(self, se_loss=True, se_weight=0.2, nclass=150, aux=False,
                 aux_weight=0.4, weight=None, ignore_index=-1, **kwargs):
        super(EncNetLoss, self).__init__(weight, None, ignore_index)
        self.se_loss = se_loss
        self.aux = aux
        self.nclass = nclass
        self.se_weight = se_weight
        self.aux_weight = aux_weight
        self.bceloss = nn.BCELoss(weight)

    def forward(self, *inputs):
        preds, target = tuple(inputs)
        inputs = tuple(list(preds) + [target])
        if not self.se_loss and not self.aux:
            return super(EncNetLoss, self).forward(*inputs)
        elif not self.se_loss:
            pred1, pred2, target = tuple(inputs)
            loss1 = super(EncNetLoss, self).forward(pred1, target)
            loss2 = super(EncNetLoss, self).forward(pred2, target)
            return loss1 + self.aux_weight * loss2
        elif not self.aux:
            pred, se_pred, target = tuple(inputs)
            se_target = self._get_batch_label_vector(target, nclass=self.nclass).type_as(pred)
            loss1 = super(EncNetLoss, self).forward(pred, target)
            loss2 = self.bceloss(torch.sigmoid(se_pred), se_target)
            return loss1 + self.se_weight * loss2
        else:
            pred1, se_pred, pred2, target = tuple(inputs)
            se_target = self._get_batch_label_vector(target, nclass=self.nclass).type_as(pred1)
            loss1 = super(EncNetLoss, self).forward(pred1, target)
            loss2 = super(EncNetLoss, self).forward(pred2, target)
            loss3 = self.bceloss(torch.sigmoid(se_pred), se_target)
            return loss1 + self.aux_weight * loss2 + self.se_weight * loss3

    @staticmethod
    def _get_batch_label_vector(target, nclass):
        # target is a 3D Variable BxHxW, output is 2D BxnClass
        batch = target.size(0)
        tvect = Variable(torch.zeros(batch, nclass))
        for i in range(batch):
            hist = torch.histc(target[i].cpu().data.float(),
                               bins=nclass, min=0,
                               max=nclass - 1)
            vect = hist > 0
            tvect[i] = vect
        return tvect
