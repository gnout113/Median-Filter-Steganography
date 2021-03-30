import cv2
import math
import os
import sys
import numpy as np
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto import Random
from numba import jit, cuda 

# Convert text to binary
# @jit
def text_to_binary(text):
	bin_text = ""
	for i in text:
		if (i == " "):
			bin_text += "00100000"
		else:
			bin_text += bin(ord(i))
	return bin_text.replace("b", "")

# Convert binary to text
# @jit
def binary_to_text(bin_num):
	return ''.join(chr(int(bin_num[i*8:i*8+8],2)) for i in range(len(bin_num)//8))

# Convert decimal to binary
# @jit
def decimal_to_binary(dec_num):
	result = "{0:b}".format(dec_num)
	i = 1
	while i == 1:
		if (len(result) < 8):
			result = "0" + result
		elif(len(result) == 8):
			break
	return result

# Convert binary to decimal
# @jit
def binary_to_decimal(bin_num):
	bin_num = list(bin_num)
	value = 0
	for i in range(len(bin_num)):
		digit = bin_num.pop()
		if digit == '1':
			value = value + math.pow(2, i)
	return value

# Encrypt image
def encrypt(key, filename):
    chunksize = 64 * 1024
    outputFile = "(encrypted)" + filename
    filesize = str(os.path.getsize(filename)).zfill(16)
    IV = Random.new().read(16)

    encryptor = AES.new(key, AES.MODE_CBC, IV)

    with open(filename, 'rb') as infile:
        with open(outputFile, 'wb') as outfile:
            outfile.write(filesize.encode('utf-8'))
            outfile.write(IV)

            while True:
                chunk = infile.read(chunksize)

                if len(chunk) == 0:
                    break
                elif len(chunk) % 16 != 0:
                    chunk += b' ' * (16 - (len(chunk) % 16))

                outfile.write(encryptor.encrypt(chunk))

# Decrypt image
def decrypt(key, filename):
    chunksize = 64 * 1024
    outputFile = filename[11:]

    with open(filename, 'rb') as infile:
        filesize = int(infile.read(16))
        IV = infile.read(16)

        decryptor = AES.new(key, AES.MODE_CBC, IV)

        with open(outputFile, 'wb') as outfile:
            while True:
                chunk = infile.read(chunksize)

                if len(chunk) == 0:
                    break

                outfile.write(decryptor.decrypt(chunk))
            outfile.truncate(filesize)

def get_key(password):
    hasher = SHA256.new(password.encode('utf-8'))
    return hasher.digest()

# Giấu Tin Trong Ảnh
@jit                                	
def hide_message(msg, password_a, password_b):
	img_name = "source_img.png"
	source_img = cv2.imread(img_name)
	hash_key_a = get_key(password_a)
	hash_key_b = get_key(password_b)
	end_of_msg = text_to_binary("@")
	bin_msg = text_to_binary(msg) + end_of_msg
	img_height = source_img.shape[0]
	img_width = source_img.shape[1]

	# Embed message(binary form) in 4 LSB’s of each RGB 
	a = 0
	b = 4
	for x in range(0,img_height):
		if(b > len(bin_msg)):
			break		
		for y in range(0,img_width):
			if(b > len(bin_msg)):
				break
			for z in range(0,3):
				if(b > len(bin_msg)):
					break
				temp = decimal_to_binary(source_img[x][y][z])
				temp = temp.replace(temp[-4:], bin_msg[a:b])
				temp = binary_to_decimal(temp)
				source_img[x][y][z] = temp
				a += 4
				b += 4

	# Median filter			
	enhanced_img = cv2.medianBlur(source_img, 5)
	enhanced_img_name = "(enhanced)" + img_name
	cv2.imwrite(enhanced_img_name, enhanced_img)

	# Subtract stego image and enhanced image
	enhanced_img = np.int16(enhanced_img)
	source_img = np.int16(source_img)
	subtracted_img = cv2.subtract(source_img,enhanced_img)
	subtracted_img_name = "(subtracted)" + img_name

	# Create a image contain negative pixel only
	negative_subtracted_img = np.zeros((img_height,img_width,3), np.uint8)
	for q in range(0,img_height):
		for w in range(0,img_width):
			for e in range(0,3):
				if(subtracted_img[q][w][e] < 0):
					negative_subtracted_img[q][w][e] = subtracted_img[q][w][e]

	subtracted_img = np.uint8(subtracted_img)				
	cv2.imwrite(subtracted_img_name, subtracted_img)
	cv2.imwrite("(negative)" + subtracted_img_name, negative_subtracted_img)
	cv2.destroyAllWindows()

	# Encrypt the subtracted image with a private key
	encrypt(hash_key_a, subtracted_img_name)
	encrypt(hash_key_b, "(negative)" + subtracted_img_name)
	os.remove(subtracted_img_name)
	os.remove("(negative)" + subtracted_img_name)  

	print ("Xong !\n")
	print("Enter de tiep tuc.")	
	input()

@jit
def reveal_message(password_a, password_b):	
	decrypt(get_key(password_a), "(encrypted)(subtracted)source_img.png")
	decrypt(get_key(password_b), "(encrypted)(negative)(subtracted)source_img.png")

	subtracted_img = cv2.imread("(subtracted)source_img.png")
	negative_subtracted_img = cv2.imread("(negative)(subtracted)source_img.png")
	enhanced_img = cv2.imread("(enhanced)source_img.png")

	# Add subtracted image and enhanced image
	img_height = enhanced_img.shape[0]
	img_width = enhanced_img.shape[1]
	enhanced_img = np.int16(enhanced_img)
	subtracted_img = np.int16(subtracted_img)
	negative_subtracted_img = np.int16(negative_subtracted_img)

	for a in range(0,img_height):
		for b in range(0,img_width):
			for c in range(0,3):
				if(negative_subtracted_img[a][b][c] != 0):
					negative_subtracted_img[a][b][c] = negative_subtracted_img[a][b][c] - 256
					subtracted_img[a][b][c] = negative_subtracted_img[a][b][c]					
	
	stego_img = cv2.add(enhanced_img, subtracted_img)

	bin_msg = ""
	result = ""
	end_of_msg = "@"
	count = 0
	for x in range(0,1):
		for y in range(0,1000):
			for z in range(0,3):
				bin_msg += decimal_to_binary(stego_img[x][y][z])[-4:]
				result = binary_to_text(bin_msg)		
				if (result[-len(end_of_msg):] == end_of_msg):
					break
			if (result[-len(end_of_msg):] == end_of_msg):
				break
		if (result[-len(end_of_msg):] == end_of_msg):
			break					

	print("Hidden message: " + result[:-1])
	cv2.destroyAllWindows()
	print()
	print("Enter de tiep tuc.")	
	input()


def main():
	i = 1
	while i == 1:
		os.system('cls')
		print("============================Giau Tin Trong File Anh Dung Filtering============================")
		choice = input("Nhap lua chon cua ban\n> 1. Giau tin \n> 2. Lay tin\n> 3. Exit\n>>> ")
		
		if (choice == "1"):
			os.system('cls')
			msg = input("Nhap tin can giau: ")
			password_a = input("Nhap password 1: ")
			password_b = input("Nhap password 2: ")
			hide_message(msg, password_a, password_b)

		elif (choice == "2"):
			os.system('cls')
			password_1 = input("Nhap password 1: ")
			password_2 = input("Nhap password 2: ")
			try:
				reveal_message(password_1, password_2)
			except:
				print("Mat khau khong dung !!!")
				sys.exit(0)	

		elif (choice == "3"):
			print ("Exit !")
			break
		else:
			print("Lua chon khong hop le !!!")
			print("Enter de tiep tuc.")	
			input()

if __name__ == "__main__":
    main()


# hide_message("testing testing","1234","1234")
# decrypt(get_key("1234"), "(encrypted)(subtracted)source_img.png")
# decrypt(get_key("1234"), "(encrypted)(negative)(subtracted)source_img.png")
# reveal_message()
# # str1 = "123456789fffff"
# # if ("123" in str1):
# # print (str1[:-4])
# print(text_to_binary("hi iam tuong"))


