"""

https://medium.com/techiepedia/binary-image-classifier-cnn-using-tensorflow-a3f5d6746697

https://www.kaggle.com/datasets/samuelcortinhas/cats-and-dogs-image-classification?resource=download-directory

https://www.tensorflow.org/tutorials/images/classification?hl=es-419

"""
from torchview import draw_graph

#import matplotlib as mpl
#mpl.rcParams['font.size'] = 15
import matplotlib.pyplot as plt
import numpy as np
import os
import PIL
import tensorflow as tf

from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.models import Sequential




class CNNEValuacion ():

    class MyEpochListener(keras.callbacks.Callback):
        def on_epoch_end(self, epoch, logs=None):
            # 'epoch' is 0-indexed integer
            # 'logs' is a dict containing metrics (e.g., loss, accuracy)
            print(f"\nEpoch {epoch + 1} just finished!")
            if logs:
                print(f"Current loss: {logs.get('loss'):.4f}")
                #print(f"Current loss: {logs.get('loss'):.4f}")
                if self.emisor is not None: self.emisor.emit(self.indice) 
                self.indice+=1
        def __init__(self,emisor,indice):
            self.emisor=emisor
            self.indice=indice


    def __init__(self, dir_name,epochs=120, learning_rate=0.0015):
        self.data_dir = dir_name
        self.epochs= epochs
        self.learning_rate=learning_rate

    def evaluate (self, emisor=None, indice=50):
        # Microalgae dataset folder to train a CNN
    #    data_dir="Dataset_Extendido2"
    #    data_dir="GithubRepo/18Agosto/18Agosto"
        data_dir=self.data_dir
        self.emisor =emisor
        self.indice=indice


        # Define the schedule (not in original repository)
        lr_schedule = tf.keras.optimizers.schedules.ExponentialDecay(
            initial_learning_rate=1e-2,
            decay_steps=10000,
            decay_rate=0.96,
            staircase=True
        )

        if emisor is not None: emisor.emit(indice) 
        indice+=1

        # Training PARAMETERS !!!!
        epochs=self.epochs
        img_height=30
        img_width=30
        batch_size = 16
        LearningRate=self.learning_rate 
        optimizer= keras.optimizers.SGD(learning_rate=lr_schedule)


        train_ds = tf.keras.utils.image_dataset_from_directory(
          data_dir,
          validation_split=0.2,
          subset="training",
          seed=123,
          image_size=(img_height, img_width),
          batch_size=batch_size)

        if emisor is not None: emisor.emit(indice) 
        indice+=1

        val_ds = tf.keras.utils.image_dataset_from_directory(
          data_dir,
          validation_split=0.2,
          subset="validation",
          seed=123,
          image_size=(img_height, img_width),
          batch_size=batch_size)

        class_names = train_ds.class_names

        print (class_names)

        if emisor is not None: emisor.emit(indice) 
        indice+=1

        AUTOTUNE = tf.data.AUTOTUNE
        train_ds = train_ds.cache().shuffle(1000).prefetch(buffer_size=AUTOTUNE)
        val_ds = val_ds.cache().prefetch(buffer_size=AUTOTUNE)


        data_augmentation = keras.Sequential(
          [
            #layers.RandomFlip("horizontal",
            layers.RandomFlip("horizontal_and_vertical",input_shape=(img_height, img_width, 3)),
            layers.RandomContrast(factor=0.2),
            layers.RandomBrightness(factor=0.3),
            layers.RandomRotation(0.1),
            #layers.RandomZoom(height_factor=0.8, width_factor=0.8),
            #layers.RandomTranslation(height_factor=0.2, width_factor=0.2),
            #layers.RandomZoom(0.1),
          ]
        )

        num_classes = len(class_names)

        model = Sequential([
          #resize_and_rescale,
          data_augmentation,
          layers.Rescaling(1./255),
          layers.Conv2D(16, 3, padding='same', activation='relu'),
          layers.MaxPooling2D(),
          layers.Conv2D(32, 3, padding='same', activation='relu'),
          layers.MaxPooling2D(),
          layers.Conv2D(64, 3, padding='same', activation='relu'),
          layers.MaxPooling2D(),
          layers.Dropout(0.2),
          layers.Flatten(),
          layers.Dense(128, activation='relu'),
          layers.Dense(num_classes, name="outputs")
        ])



        lr_schedule = keras.optimizers.schedules.ExponentialDecay(
            initial_learning_rate=LearningRate,
            decay_steps=10000,
            decay_rate=0.9)

        model.compile(optimizer=optimizer,                loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
                      metrics=['accuracy'])

        model.summary()


        history = model.fit(
          train_ds,
          validation_data=val_ds,
          epochs=epochs,
          callbacks=[self.MyEpochListener(self.emisor, self.indice)]
        )


        AccFinal = history.history['accuracy'][-1]
        print ("PRecision FINAL: ",AccFinal)

        acc = history.history['accuracy']
        val_acc = history.history['val_accuracy']

        loss = history.history['loss']
        val_loss = history.history['val_loss']

        epochs_range = range(epochs)

        plt.rcParams['font.size'] = 15
        plt.figure(figsize=(12, 12))
        plt.subplot(1, 2, 1)
        plt.plot(epochs_range, acc, label='Training Accuracy', color='red')
        plt.plot(epochs_range, val_acc, label='Validation Accuracy', color='blue')
        plt.legend(loc='lower right')
        plt.title('Training and Validation Accuracy')

        plt.subplot(1, 2, 2)
        plt.plot(epochs_range, loss, label='Training Loss', color='red')
        plt.plot(epochs_range, val_loss, label='Validation Loss', color='blue')
        plt.legend(loc='upper right')
        plt.title('Training and Validation Loss')
        #plt.show()

        plt.savefig('my_plot.png')  





        print(class_names)


#Objeto = CNNEValuacion ("18Agosto/18Agosto")
#Objeto.evaluate()


