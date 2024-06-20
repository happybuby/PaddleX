# copyright (c) 2024 PaddlePaddle Authors. All Rights Reserve.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.



import os

import numpy as np

from ....utils import logging
from ...base.predictor.transforms import image_common
from ...base import BasePredictor
from .keys import TextRecKeys as K
from . import transforms as T
from .utils import InnerConfig
from ..support_models import SUPPORT_MODELS


class TextRecPredictor(BasePredictor):
    """ TextRecPredictor """
    support_models = SUPPORT_MODELS

    def load_other_src(self):
        """ load the inner config file """
        infer_cfg_file_path = os.path.join(self.model_dir, 'inference.yml')
        if not os.path.exists(infer_cfg_file_path):
            raise FileNotFoundError(
                f"Cannot find config file: {infer_cfg_file_path}")
        return InnerConfig(infer_cfg_file_path)

    @classmethod
    def get_input_keys(cls):
        """ get input keys """
        return [[K.IMAGE], [K.IM_PATH]]

    @classmethod
    def get_output_keys(cls):
        """ get output keys """
        return [K.REC_PROBS]

    def _run(self, batch_input):
        """ run """
        images = [data[K.IMAGE] for data in batch_input]
        input_ = np.stack(images, axis=0)
        if input_.ndim == 3:
            input_ = input_[:, np.newaxis]
        input_ = input_.astype(dtype=np.float32, copy=False)
        outputs = self._predictor.predict([input_])

        probs_res = outputs[0]

        # In-place update
        pred = batch_input
        for dict_, probs in zip(pred, probs_res):
            dict_[K.REC_PROBS] = probs[np.newaxis, :]
        return pred

    def _get_pre_transforms_for_data(self, data):
        """ _get_pre_transforms_for_data """
        if K.IMAGE not in data and K.IM_PATH not in data:
            raise KeyError(
                f"Key {repr(K.IMAGE)} or {repr(K.IM_PATH)} is required, but not found."
            )
        pre_transforms = []
        if K.IMAGE not in data:
            pre_transforms.append(image_common.ReadImage())
        else:
            pre_transforms.append(image_common.GetImageInfo())
        pre_transforms.append(T.OCRReisizeNormImg())
        return pre_transforms

    def _get_post_transforms_for_data(self, data):
        """ get postprocess transforms """
        post_transforms = [T.CTCLabelDecode(self.other_src.PostProcess)]
        if data.get('cli_flag', False):
            output_dir = data.get("output_dir", "./")
            post_transforms.append(T.PrintResult())
        return post_transforms
