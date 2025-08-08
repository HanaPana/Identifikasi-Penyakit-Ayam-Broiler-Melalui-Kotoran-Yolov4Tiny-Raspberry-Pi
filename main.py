import cv2
import time
import threading
import RPi.GPIO as GPIO
import numpy as np
import telebot
import logging
from telebot import types
from datetime import datetime, timedelta
from picamera2 import Picamera2
from gpiozero import LED
import cProfile

#token bot
bot = telebot.TeleBot('7958361007:AAEi3sHloPfYHe-lmJuTVSOgKt-mTeYhbD8')
chat_id = 1496177203

#untuk menyimpan daftar log pesan yang sudah dikirim di dalam sebuah file
logging.basicConfig(
    filename="/home/thyas/tugas_akhir/bot/bot_message_log.txt",
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

#untuk threading dan telegram
detected_objects = []
lock = threading.Lock()
detection_started = False

#Button
GPIO.setmode(GPIO.BCM)
GPIO.setup(26, GPIO.IN, pull_up_down=GPIO.PUD_UP)

#LED
redPin = LED(25)
greenPin = LED(23)
bluePin = LED(24)

#untuk kelas sakit
def red():
    redPin.on()
    greenPin.off()
    bluePin.off()

#untuk kelas sehat
def green():
    redPin.off()
    greenPin.on()
    bluePin.off()
    
def off():
    redPin.off()
    greenPin.off()
    bluePin.off()
    
#camera
cam = Picamera2()
width = 2000
height = 600
cam.configure(cam.create_video_configuration(main={"format": 'RGB888', "size": (width, height)}, lores={"size": (600, 480)}, display="lores"))

#YOLO
net = cv2.dnn.readNetFromDarknet("yolov4-tiny-custom.cfg", "yolov4-tiny-custom_best.weights")
classes = ['coccidiosis', 'healthy', 'newcastle', 'salmonella']
sick_classes = ['coccidiosis', 'newcastle', 'salmonella']
current_classes = classes
current_net = net

#camera on
cam.start()

# definisikan null bounding boxes untuk per tiap area kandang
bounding_boxes = [
    {"x": 1, "y": 1, "width": 404, "height": 888, "kandang": "A"},
    {"x": 413, "y": 1, "width": 400, "height": 898, "kandang": "B"},
    {"x": 816, "y": 1, "width": 400, "height": 893, "kandang": "C"},
    {"x": 1216, "y": 1, "width": 412, "height": 893, "kandang": "D"},
    {"x": 1631, "y": 1, "width": 363, "height": 876, "kandang": "E"}
]

#caption untuk foto
caption = {
    "sick" : "{current_time} | System detected there are sick feces in the cage {regions_str}. Please immediately check the poultries now.",
    "healthy" : "{current_time} | System doesn't detect any sick feces in the cage. All poultries are in good condition.",
    "none" : "{current_time} | System does not detect any sick nor healthy feces in the poultries' cages."
    }    

#melihat log hanya untuk kotoran yang adanya pendeteksian untuk kotoran sakit
def log_detection_event(class_label, regions_str):
    if class_label in sick_classes:    
        detection_message = f"Sick Feces ({class_label}) in cage {regions_str}."
    elif class_label == "healthy":
        detection_message = f"Healthy Feces."
    else:
        detection_message = f"No sick feces detected."
    
    logging.info(detection_message)

#object detection
def obj_detection():          
    #Memeriksa apakah sistem dapat mengirim pesan (interval 15 menit)
    def can_send_image():
        global last_message_time
        current_time1 = datetime.now()        
        if 'last_message_time' not in globals():
            last_message_time = current_time1
            return True
        if current_time1 - last_message_time >= timedelta(minutes=15):
            last_message_time = current_time1
            return True
        return False
    
    #mengirimkan image ke telegram ketika sudah memasuki waktu intervalnya
    def send_image(frame, current_time):
        global sick_detected, num
        cv2.imwrite(out_path, frame)
        with open(out_path, 'rb') as photo:
            if class_label in sick_classes:
                for obj, regions in alerts.items():
                    regions_str = ", ".join(regions)
                    caption_text = caption["sick"].format(current_time=current_time, regions_str=regions_str)
                    bot.send_photo(chat_id, photo, caption_text)                           
                    log_detection_event(class_label, regions_str)
                    break
            elif class_label == 'healthy' and not sick_detected:
                caption_text = caption["healthy"].format(current_time=current_time, regions_str=None)
                bot.send_photo(chat_id, photo, caption_text)
                log_detection_event(class_label, None)
            elif not class_label and not sick_detected:
                caption_text = caption["none"].format(current_time=current_time, regions_str=None)
                bot.send_photo(chat_id, photo, caption_text)
                log_detection_event(label, regions_str = None)
        num += 1
        captured_label.clear()
    
    #mengirimkan image ke telegram versi button
    def send_image_button(frame, current_time, detected_objects):
        global sick_detected, num
        try:
            cv2.imwrite(out_path1, frame)
            detected_labels = detected_objects
            with open(out_path1, 'rb') as photo:
                if any(label in sick_classes for label in detected_labels):  # If any of the detected labels is a sick class
                    for obj, regions in alerts.items():
                        regions_str = ", ".join(regions)
                        caption_text = caption["sick"].format(current_time=current_time, regions_str=regions_str)
                        bot.send_photo(chat_id, photo, caption_text)
                        log_detection_event(detected_labels, regions_str)
                        break
                elif 'healthy' in detected_labels and not sick_detected:
                    caption_text = caption["healthy"].format(current_time=current_time, regions_str=None)
                    bot.send_photo(chat_id, photo, caption_text)
                    log_detection_event(detected_labels, None)
                elif not detected_labels and not sick_detected:
                    caption_text = caption["none"].format(current_time=current_time, regions_str=None)
                    bot.send_photo(chat_id, photo, caption_text)
                    log_detection_event(detected_labels, regions_str=None)
        finally:
            print("photo sent!")
            num += 1
            captured_label.clear()
    
    # memeriksa apakah objek berada pada region/null bounding boxes
    def is_object_in_region(object_coords, region):
        try:
            #memeriksa x, y, lebar dan tinggi
            obj_center = (object_coords[0] + object_coords[2] / 2, object_coords[1] + object_coords[3] / 2)
            region_center = (region["x"] + region["width"] / 2, region["y"] + region["height"] / 2)
            # threshold berdasarkan region
            threshold = max(region["width"], region["height"], 10)
            return abs(obj_center[0] - region_center[0]) < threshold and abs(obj_center[1] - region_center[1]) < threshold
        except (TypeError, KeyError) as e:
            print(f"Error accessing region data: {e}")
            return False
    
    #memeriksa posisi objek di region/null bounding box yang mana
    def region_check(detected_obj, region):   
        detected_regions = []
        alerted_region.clear()
        for obj in detected_obj:
            for region in bounding_boxes:
                if region['kandang'] not in alerted_region and is_object_in_region(boxloc, region):
                    print(f"Alert: Object detected in {region['kandang']}")
                    detected_regions.append(region['kandang'])
                    alerted_region.add(region['kandang'])
            if detected_regions:
                alerts[obj] = detected_regions 
    
    global detection_started
    global last_log_message
    global sick_detected
    global num
    
    try:
        while True:            
            if not detection_started:
                time.sleep(1)
                continue
            
            confidence_threshold = 0.1
            nms_threshold = 0.2
            
            #untuk alert region tempat daerah sakit
            alerts = {}
            alerted_region = set()
            button_label = set()
            
            num = 0
            frame = cam.capture_array()
            
            blob = cv2.dnn.blobFromImage(frame, 1 / 255, (600, 600), (0, 0, 0), swapRB=True, crop=False)
            current_net.setInput(blob)
            output_layer_names = current_net.getUnconnectedOutLayersNames()
            outputs = current_net.forward(output_layer_names)

            boxes = []
            confidences = []
            class_ids = []

            for output in outputs:
                for detection in output:
                    scores = detection[5:]
                    class_id = np.argmax(scores)
                    confidence = scores[class_id]

                    if confidence > confidence_threshold:
                        if class_id < len(current_classes): 
                            class_label = current_classes[class_id]
                        else:
                            class_label = 'Unknown'
                            confidence = 0

                        center_x = int(detection[0] * width)
                        center_y = int(detection[1] * height)
                        w = int(detection[2] * width)
                        h = int(detection[3] * height)

                        x = int(center_x - w / 2)
                        y = int(center_y - h / 2)
                        min_dim = min(w, h)
                        new_x = int(center_x - min_dim / 2)
                        new_y = int(center_y - min_dim / 2)
                        new_w = new_h = min_dim

                        boxloc = (x, y, w, h) 
                        boxes.append([x, y, w, h])
                        confidences.append(float(confidence))
                        class_ids.append(class_id)

            indices = cv2.dnn.NMSBoxes(boxes, confidences, confidence_threshold, nms_threshold)
            font = cv2.FONT_HERSHEY_SIMPLEX
            colors = np.random.uniform(0, 255, size=(len(boxes), 3))
            
            #waktu dan tanggal sekarang
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
            #path asal foto
            out_path = f"/home/thyas/tugas_akhir/TES_FOTO/I | {current_time} | {num}.jpg"
            out_path1 = f"/home/thyas/tugas_akhir/TES_FOTO/B | {current_time} | {num}.jpg"
            
            #meletakkan waktu
            cv2.putText(frame, current_time, (1, 25), font, 1, (255, 255, 0), 2)
            
            sick_detected = False
            
            with lock:
                detected_objects.clear()
                captured_label = []
                if len(indices) > 0: 
                    for i in indices:
                        if isinstance(i, (list, tuple, np.ndarray)):
                            i = i[0]  

                        x, y, w, h = boxes[i]
                        class_id = class_ids[i]
                        confidence = confidences[i]

                        if class_id < len(current_classes):
                            class_label = current_classes[class_id]
                        else:
                            class_label = 'Unknown'
                            confidence = 0

                        detected_objects.append({'class': class_label, 'confidence': confidence})
                        
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                        label = f"{class_label}: {confidence:.2f}"
                        cv2.putText(frame, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                                          
                        captured_label.append(class_label)
                        
                        #pelabelan nya
                        if class_label in sick_classes:
                            sick_detected = True
                            red()
                            region_check(boxloc, bounding_boxes)
                            if can_send_image():
                                send_image(frame, current_time)
                            print("Kotoran sakit terdeteksi")
                        elif class_label == 'healthy' and not sick_detected:
                            green()
                            if can_send_image():
                                send_image(frame, current_time)
                            print("Kotoran sehat terdeteksi")
                        elif class_label == None and not sick_detected:
                            off()
                            if can_send_image():
                                send_image(frame, current_time)
                            print("Tidak ada kotoran yang terdeteksi.")
               
               #untuk push button
                if GPIO.input(26) == GPIO.LOW:
                    bot.send_message(chat_id, "The button has been pressed, please wait...")
                    send_image_button(frame, current_time, captured_label)
                    # Wait for button release to avoid multiple captures
                    while GPIO.input(26) == GPIO.LOW:
                        time.sleep(0.5)
                
                cv2.imshow('deteksi', frame)
                if cv2.waitKey(1) == ord('q'):
                        break
    finally:        
        cv2.destroyAllWindows()
        GPIO.cleanup()
        
@bot.callback_query_handler(func=lambda call: call.data == 'begin')
def start_button_callback(call):
    global detection_started
    detection_started = True
    bot.answer_callback_query(call.id)  # Acknowledge the button press
    bot.edit_message_text("The system has started. Opening the camera...", chat_id=call.message.chat.id, message_id=call.message.message_id)

@bot.message_handler(commands=['start'])
def handle_start(message):
    global detection_started
    if detection_started == False:
        detection_started = True
        bot.send_message(message.chat.id, "System has start.")
    else:
        bot.send_message(message.chat.id, "System is ongoing. Please use the command /stop to pause the system.")
    
@bot.message_handler(commands=['stop'])
def handle_stop(message):
    global detection_started
    if detection_started == True:
        detection_started = False
        bot.send_message(message.chat.id, "System has been stopped.")
        off()
        cv2.destroyAllWindows()
    else :
        bot.send_message(message.chat.id, "System is stopped temporarily. Please use the command /start to start the sytem again.")

@bot.message_handler(commands=['info'])
def handle_info(message):
    bot.send_message(message.chat.id, "This bot functions to send message to user regarding poultries health condition by recognizing specific diseases (Coccidiosis, Newcastle, Salmonella). System will send information every 15 minutes or can be done manually by pressing the push button.")

@bot.message_handler(commands=['check'])
def handle_check(message):
    global detection_started
    if detection_started:
        bot.send_message(message.chat.id, "System has started.")
    else:
        bot.send_message(message.chat.id, "System has not started.")
        
@bot.message_handler(commands=['log'])
def handle_log(message):
    try:
        # Read the log file
        with open("/home/thyas/tugas_akhir/bot/bot_message_log.txt", 'r') as log_file:
            log_content = log_file.read()
        
        # Send the log content as a message to the user (limited to 4000 characters)
        if log_content:
            bot.send_message(message.chat.id, log_content[-4000:])
        else:
            bot.send_message(message.chat.id, "No history available.")
    
    except FileNotFoundError:
        bot.send_message(message.chat.id, "Log file not found.")
    except Exception as e:
        bot.send_message(message.chat.id, f"Error reading log: {e}")

@bot.message_handler(commands=['help'])
def handle_help(message):
    help_text = """
    Available Commands:
    - /start	: Start the system.
    - /info 	: See short information about the system.
    - /check 	: Check System status connection.
    - /help 	: Check available commands.
    - /log 		: Check Detection history log.
    - /stop 	: Stop the system temporarily.
    """
    bot.reply_to(message, help_text)

@bot.message_handler(func=lambda message: True)
def handle_unknown(message):
    if message.text.startswith('/'):
        bot.send_message(message.chat.id, "Command is unknown. Please check the spellings or any mistyping.")
    else:
        bot.send_message(message.chat.id, "Your message is not similar to the commands format. Please use commands such /help to see the commands that can be used.")

def send_startup_message(bot, chat_id):
    # Create the inline button
    keyboard = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton("Start", callback_data='begin')
    keyboard.add(button)

    # Send the startup message with the inline button
    bot.send_message(
        chat_id, 
        "System has been initialized. Please press the 'Start' button to start detecting.",
        reply_markup=keyboard
    )    

#threading/multiprocessing
if __name__ == "__main__":
    send_startup_message(bot, chat_id)
    
    object_detection_thread = threading.Thread(target=obj_detection)
    object_detection_thread.start()
    
    while detection_started:
        send_image_as = threading.Thread(target=send_image_button)
        send_image_as.start()

    bot.polling()
    
    cProfile.run('obj_detection()', sort='time')
