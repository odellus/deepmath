# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Convolutional+LSTM model with word embedded input -- larger version."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from keras import layers
import tensorflow as tf
from deepmath.premises import model

MOVING_AVERAGE_DECAY = .9999


class Model(model.Model):
  """Convolutional model for word embedded input."""

  def __init__(self, graph=None, embedding_size=1024):
    super(Model, self).__init__(graph=graph, embedding_size=embedding_size)

  def make_embedding(self, x):
    with self.graph.as_default():
      # 3 convolutional layers, with max pooling in the last two
      x = layers.Convolution1D(1024, 5,
                               border_mode='valid',
                               subsample_length=1,
                               activation='relu')(x)
      x = layers.Convolution1D(1024, 5,
                               border_mode='valid',
                               subsample_length=1,
                               activation='relu')(x)
      x = layers.MaxPooling1D(2, stride=2)(x)
      x = layers.Convolution1D(self.embedding_size, 5,
                               border_mode='valid',
                               subsample_length=1,
                               activation='relu')(x)
      x = layers.MaxPooling1D(2, stride=2)(x)

      # Use an LSTM to finish off
      initializer = tf.truncated_normal_initializer(stddev=0.01, seed=1337)
      cell = tf.contrib.rnn.LSTMCell(self.embedding_size,
                                     use_peepholes=False,
                                     initializer=initializer,
                                     num_proj=None,
                                     num_unit_shards=1,
                                     num_proj_shards=1,
                                     forget_bias=1.0,
                                     state_is_tuple=False)
      x, _ = tf.nn.dynamic_rnn(cell, x,
                               sequence_length=None,
                               initial_state=None,
                               dtype='float32',
                               parallel_iterations=32,
                               swap_memory=False)
      last_timestep = tf.shape(x)[1]
      indices = tf.stack([0, last_timestep - 1, 0])
      indices = tf.cast(indices, 'int32')
      embedded = tf.slice(x, indices, [-1, 1, -1])
      embedded = tf.squeeze(embedded, [1])
      embedded.set_shape((None, self.embedding_size))
    return embedded

  def conjecture_embedding(self, conjectures):
    """Compute the embedding for each of the conjectures."""
    with tf.variable_scope('conjecture'):
      return self.make_embedding(conjectures)

  def axiom_embedding(self, axioms):
    """Compute the embedding for each of the axioms."""
    with tf.variable_scope('axiom'):
      return self.make_embedding(axioms)

  def classifier(self, conjecture_embedding, axiom_embedding):
    """Compute the logits from conjecture and axiom embeddings."""
    with self.graph.as_default():
      net = tf.concat((conjecture_embedding, axiom_embedding), 1)
      net = tf.contrib.layers.relu(net, 1024)
      logits = tf.contrib.layers.linear(net, 2)
    return logits
