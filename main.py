# UCF Senior Design 2017-18
# Group 38

import cv2
import gc
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import ObjectProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from PIL import Image
import os
import utils.blur as blur
import utils.compare as compare
import utils.global_var as gv

# all accepted images will be written to a subdirectory
# named 'processed'
DES_NAME = 'processed'


def img_handler(img_path):
    """
    Determine whether or not a given file is an image
        img_path: (String) path to the file
    """
    try:
        # file is an image
        img = Image.open(img_path)
        img.close()
        return True

    except IOError:
        # file is not an image
        return False


class LandingScreen(Screen):
    """
    This is the splash screen; It displays the team name and logo for three
    seconds. User may move on to next screen by pressing on it
    """

    def __init__(self, **kwargs):
        """
        Display screen for three seconds
        """
        super(LandingScreen, self).__init__(**kwargs)
        Clock.schedule_once(self.switch, 3)

    def switch(self, dt):
        """
        Switch to folder selection screen
        """
        self.manager.current = 'folder_select'


class FolderSelectScreen(Screen):
    """
    This screen is where users can select their input folder and toggle on/off
    the image comparison option
    """
    loadFile = ObjectProperty(None)

    def dismiss_popup(self):
        self._popup.dismiss()

    def show_load(self):
        """
        Create a pop-up inside the window to select a folder
        """
        content = LoadDialog(load=self.load, cancel=self.dismiss_popup)
        self._popup = Popup(title="Select folder", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()

    def load(self, path, filename):
        """
        Load the selected path
        """

        # store user-selected path
        gv.dir_path = path
        # determine how many files are in the path
        gv.num_files = len(os.listdir(gv.dir_path))

        self.update_path(gv.dir_path)
        self.dismiss_popup()

    def update_path(self, dir_path):
        """
        Display the selected path for user to see
        """
        # only display relative path
        new_text = "Directory Name: " + \
            os.path.normpath(os.path.basename(dir_path))
        # update the path to show to user
        self.ids.path.text = new_text

    def check_path(self):
        """
        Check if the user has selected an input folder
        """
        if not gv.dir_path == "":
            # begin processing images if a path is given
            # switch to transition screen
            self.manager.current = 'black1'
        else:
            # if no path was given, prompt user for one
            self.ids.path.text = "No directory path given"

    def update_toggle(self):
        """
        Update whether application will implement image comparison
        depending on state of toggle button
        """
        if self.ids.choice.active:
            gv.comp = 1
        else:
            gv.comp = 0


class BlackScreen1(Screen):
    """
    Transition screen
    """

    def switch(self, dt):
        """
        Switch to progress screen to begin application
        """
        self.manager.current = 'progress'


class ProgressScreen(Screen):
    """
    This screen is where the classification model will be loaded. It
    also acts as a transition from folder selection to the beginning of
    the application process
    """

    def switch(self, dt):
        """
        Load the classification model and switch to next screen to begin
        processing images
        """
        # load the model if it has not been done
        if not gv.load:
            import architectures.buff_bobo.classifier as cl
            gv.model = cl.ClassificationModel(
                (112, 112), 'output/buff_bobo-670')
            # update that model has been loaded
            gv.load = 1

        # switch to transition screen
        self.manager.current = 'black2'


class BlackScreen2(Screen):
    """
    Transition screen
    """

    def switch(self, dt):
        """
        Switch to process screen to begin processing images
        """
        self.manager.current = 'process'


class ProcessScreen(Screen):
    """
    This screen is where all the images get processed. The steps are:
        1) blur detection
        2) bird classification
        3) bird localization
        4) face classification
        5) face localization

    The images and its results for each respective steps are displayed in
    real-time. Images are initially added to a global dictionary organized
    as {filename: numpy array} and get removed one-by-one every time an image
    fails a processing step
    """

    def update(self, dt):
        """
        Display processing results to screen in real-time for user to see
        """
        # if blur detection has not been implemented
        if not gv.blur_step:
            # preventive measure: avoid out-of-index error
            if gv.index < gv.num_files:
                file_path = os.path.join(
                    gv.dir_path, os.listdir(gv.dir_path)[gv.index])

                # avoid nonimages and hidden files
                if img_handler(file_path):
                    # if this is the first pass into this step of the process,
                    # update the title of the process for user to see
                    if not gv.first_pass:
                        gv.first_pass = 1
                        # update stage of processing
                        self.ids.message.text = 'B L U R   D E T E C T I O N'
                        # remove image transparency
                        self.ids.image.color = (1, 1, 1, 1)

                    # display working image
                    self.ids.image.source = file_path
                    # reset result and add transparency back
                    self.ids.result.color = (0, 0, 0, 0)
                    self.ids.result.source = ''

                    # call blur detection on image
                    self.check_blur(file_path, os.listdir(gv.dir_path)[gv.index])

                # continue to next image
                gv.index += 1

            # implemented blur detection on all images
            # update and move to next step
            else:
                gv.index = 0
                gv.first_pass = 0
                gv.files = list(gv.images.keys())
                gv.blur_step = 1

        # if bird classification has not been implemented
        elif not gv.bird_step:
            # preventive measure: avoid out-of-index error
            if gv.index < len(gv.files):
                file_path = os.path.join(gv.dir_path, gv.files[gv.index])

                # if this is the first pass into this step of the process,
                # update the title of the process for user to see
                if not gv.first_pass:
                    gv.first_pass = 1
                    # update stage of processing
                    self.ids.message.text = 'B I R D   C L A S S I F I C A T I O N'
                    # remove image transparency
                    self.ids.image.color = (1, 1, 1, 1)

                # display working image
                self.ids.image.source = file_path
                # reset result and add transparency back
                self.ids.result.color = (0, 0, 0, 0)
                self.ids.result.source = ''

                # call object classification on image
                self.check_class(gv.images[gv.files[gv.index]], gv.files[gv.index])

                # continue to next image
                gv.index += 1

            # implemented bird classification on all images
            # update and move to next step
            else:
                gv.index = 0
                gv.files = list(gv.images.keys())
                gv.bird_step = 1

        # all images have been processed successfully
        # update and move to next screen
        else:
            gv.index = 0

            # the folder path where all accepted images will be written
            gv.des_path = os.path.join(gv.dir_path, DES_NAME)

            # create the folder if it does not exist
            if not os.path.isdir(gv.des_path):
                os.makedirs(gv.des_path)

            gv.files = list(gv.images.keys())

            # switch to transition screen
            self.manager.current = 'black3'

            # collect any garbage not already gathered by python
            gc.collect()

            # unschedule kivy's Clock.schedule_interval() function
            return False

    def check_blur(self, img, filename):
        """
        Detect if an image is blurry and display results
        """
        image, result = blur.detect_blur(img)

        # image is not blurry
        if result:
            # remove image transparency and display green check
            self.ids.result.color = (1, 1, 1, 1)
            self.ids.result.source = 'assets/yes.png'

            # add non-blurry image to image dictionary
            gv.images[filename] = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # image is blurry
        else:
            # remove image transparency and display red x
            self.ids.result.color = (1, 1, 1, 1)
            self.ids.result.source = 'assets/no.png'

    def check_class(self, img, filename):
        """
        Classify if an image contains a bird and display results
        """
        resized_img = cv2.resize(img, (112, 112))
        prediction = gv.model.predict([resized_img])
        result = gv.model.classify(prediction)

        # image contains a bird
        if result:
            # remove image transparency and display green check
            self.ids.result.color = (1, 1, 1, 1)
            self.ids.result.source = 'assets/yes.png'

        # image does not contain a bird
        else:
            # remove image transparency and display red x
            self.ids.result.color = (1, 1, 1, 1)
            self.ids.result.source = 'assets/no.png'

            # remove image from dictionary
            gv.images.pop(filename)


class BlackScreen3(Screen):
    """
    Transition screen
    """

    def switch(self, dt):
        """
        Switch to next screen based on corner toggle button
        """
        if gv.comp:
            # switch to comparing screen
            self.manager.current = 'compare'
        else:
            # switch to writing screen
            self.manager.current = 'write'


class CompareScreen(Screen):
    """
    This screen is where the application reduces the number of similar images
    in the final subdirectory, based on user choice
    """

    def compare(self, dt):
        """
        Reduce number of similar images in a dictionary and update progress bar
        """
        # set the progress bar maximum to the size of the dictionary
        length = self.ids.progress.max = len(gv.files)

        # preventive measure to avoid out-of-index error
        if gv.index < length:
            # display progress to screen
            self.ids.loading.text = "Loading " + \
                str(gv.index + 1) + " of " + str(length)

            # set a comparison standard if there is none
            if gv.std == '':
                gv.std, gv.std_hash, gv.count = compare.set_standard(
                    gv.images, gv.files[gv.index])

            else:
                # compare the standard to the working image
                result = compare.limit(
                    gv.images[gv.files[gv.index]], gv.std_hash, gv.count)

                if result == 'remove':
                    # too many similar images; remove from dictionary
                    gv.images.pop(gv.files[gv.index])
                    gv.count += 1

                elif result == 'continue':
                    # continue with same standard
                    gv.count += 1

                elif result == 'update_std':
                    # non-similar image found; update standard
                    gv.std, gv.std_hash, gv.count = compare.set_standard(
                        gv.images, gv.files[gv.index])

            # update progress bar for user to see
            self.ids.progress.value = gv.index + 1
            # continue to next image
            gv.index += 1

        # compared entire dictionary; update and move on to next screen
        else:
            gv.index = 0
            # switch to writing screen
            self.manager.current = 'write'
            gv.files = list(gv.images.keys())
            # unschedule kivy's Clock.schedule_interval() function
            return False


class WriteScreen(Screen):
    """
    This screen is where the accepted images get written into the final
    subdirectory, called 'processed'
    """

    def begin(self, dt):
        """
        Write final images to 'processed' folder and display progress for user
        """

        # set the progress bar maximum to the size of the dictionary
        length = self.ids.progress.max = len(gv.images)

        # preventive measure to avoid out-of-index error
        if gv.index < length:
            # display progress to screen
            self.ids.loading.text = "Loading " + \
                str(gv.index + 1) + " of " + str(length)

            # write accepted images to subdirectory
            self.write_to(gv.files[gv.index])

            # update progress bar for user to see
            self.ids.progress.value = gv.index + 1
            # continue to next image
            gv.index += 1

        # all images have been written; update and move on to next screen
        else:
            # reset all global variables for future passes
            gv.reset()

            # switch to end screen
            self.manager.current = 'black4'

            # unschedule kivy's Clock.schedule_interval() function
            return False

    def write_to(self, filename):
        """
        Write image to 'processed' folder
        """
        img = Image.fromarray(gv.images[filename])
        img.save(os.path.join(gv.des_path, filename))


class BlackScreen4(Screen):
    """
    Transition screen
    """

    def switch(self, dt):
        """
        Switch to end screen
        """
        self.manager.current = 'end'


class EndScreen(Screen):
    """
    This screen is where the user is notified that the process is complete
    """
    pass


class LoadDialog(FloatLayout):
    load = ObjectProperty(None)
    cancel = ObjectProperty(None)


# config.kv should not implement any screen manager stuff as it
# overrides any definitions in this file, and cause a lot of strife
Builder.load_file("config.kv")

# Create the screen manager
sm = ScreenManager(transition=FadeTransition())
sm.add_widget(LandingScreen(name='landing'))
sm.add_widget(FolderSelectScreen(name='folder_select'))
sm.add_widget(BlackScreen1(name='black1'))
sm.add_widget(BlackScreen2(name='black2'))
sm.add_widget(ProgressScreen(name='progress'))
sm.add_widget(CompareScreen(name='compare'))
sm.add_widget(BlackScreen3(name='black3'))
sm.add_widget(WriteScreen(name='write'))
sm.add_widget(BlackScreen4(name='black4'))
sm.add_widget(ProcessScreen(name='process'))
sm.add_widget(EndScreen(name='end'))


class BirdApp(App):
    """
    Kivy module
    """

    def build(self):
        self.title = ''
        # removes os-created window border
        Window.borderless = True
        return sm


Factory.register('LoadDialog', cls=LoadDialog)


if __name__ == '__main__':
    BirdApp().run()
