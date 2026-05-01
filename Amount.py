Amount =int(input("Please Enter Your Amount For Withdrawal :"))
note_100 = Amount//100
note_50 = (Amount%100)//50
note_10 = ((Amount%100)%50)//10
remainder = ((Amount % 100) % 50) % 10
print( "notes of $100 " , note_100)
print("notes of $50" , note_50)
print("notes of $10" , note_10)
print("remaining amount is " , remainder)

            