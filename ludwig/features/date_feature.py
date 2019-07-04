#! /usr/bin/env python
# coding=utf-8
# Copyright (c) 2019 Uber Technologies, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
import logging
from datetime import date
from datetime import datetime

import numpy as np
import tensorflow as tf

from ludwig.constants import *
from ludwig.features.base_feature import BaseFeature
from ludwig.features.base_feature import InputFeature
from ludwig.models.modules.date_encoders import DateEmbed, DateWave
from ludwig.utils.misc import set_default_value, get_from_registry

logger = logging.getLogger(__name__)

DATE_VECTOR_LENGTH = 8


class DateBaseFeature(BaseFeature):
    def __init__(self, feature):
        super().__init__(feature)
        self.type = DATE

    preprocessing_defaults = {
        'missing_value_strategy': FILL_WITH_CONST,
        'fill_value': '',
        'datetime_format': '%m/%d/%y %H:%M:%S'
    }

    @staticmethod
    def get_feature_meta(column, preprocessing_parameters):
        return {
            'preprocessing': preprocessing_parameters
        }

    @staticmethod
    def date_to_list(date_str, datetime_format):

        datetime_obj = datetime.strptime(date_str, datetime_format)

        yearday = (
            datetime_obj.toordinal() -
            date(datetime_obj.year, 1, 1).toordinal() + 1
        )
        return [
            datetime_obj.year,
            datetime_obj.month,
            datetime_obj.day,
            datetime_obj.weekday(),
            yearday,
            datetime_obj.hour,
            datetime_obj.minute,
            datetime_obj.second
        ]

    @staticmethod
    def add_feature_data(
            feature,
            dataset_df,
            data,
            metadata,
            preprocessing_parameters=None
    ):
        if 'datetime_format' in preprocessing_parameters:
            feature['preprocessing']['datetime_format'] = (
                preprocessing_parameters['datetime_format']
            )

        datetime_format = feature['preprocessing']['datetime_format']
        dates_to_lists = [
            np.array(DateBaseFeature.date_to_list(row, datetime_format))
            for row in dataset_df[feature['name']]
        ]

        data[feature['name']] = np.array(dates_to_lists, dtype=np.int8)


class DateInputFeature(DateBaseFeature, InputFeature):
    def __init__(self, feature):
        super().__init__(feature)

        self.encoder = 'embed'

        encoder_parameters = self.overwrite_defaults(feature)

        self.encoder_obj = self.get_date_encoder(encoder_parameters)

    def get_date_encoder(self, encoder_parameters):
        return get_from_registry(
            self.encoder, date_encoder_registry)(
            **encoder_parameters
        )

    def _get_input_placeholder(self):
        # None dimension is for dealing with variable batch size
        return tf.placeholder(
            tf.int32,
            shape=[None, DATE_VECTOR_LENGTH],
            name=self.name
        )

    def build_input(
        self,
        regularizer,
        dropout_rate,
        is_training=False,
        **kwargs
    ):
        placeholder = self._get_input_placeholder()
        logger.debug('placeholder: {0}'.format(placeholder))

        feature_representation, feature_representation_size = self.encoder_obj(
            placeholder,
            regularizer=regularizer,
            dropout_rate=dropout_rate,
            is_training=is_training
        )
        logging.debug('  feature_representation: {0}'.format(
            feature_representation))

        feature_representation = {
            'name': self.name,
            'type': self.type,
            'representation': feature_representation,
            'size': feature_representation_size,
            'placeholder': placeholder
        }
        return feature_representation

    @staticmethod
    def update_model_definition_with_metadata(
        input_feature,
        feature_metadata,
        *args,
        **kwargs
    ):
        pass

    @staticmethod
    def populate_defaults(input_feature):
        set_default_value(input_feature, 'tied_weights', None)


date_encoder_registry = {
    'embed': DateEmbed,
    'wave': DateWave
}
