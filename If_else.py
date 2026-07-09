print("1.Bike")
print("2.Car")

choice= int(input("Choose Between 1 or 2"))

if choice == 1:
    print("1.Scooty")
    print("2.Scooter")
    choice2= int(input("Choose between 1 or 2")) 
    if choice2 == 1:
        print("you have selected scooty")
    elif choice2 == 2:
        print("you have selected scooter")
    else:
        print("invalid input")
elif choice == 2:
    print("1.Sedan")
    print("2.XUV")
    choice3= int(input("Choose between 1 or 2"))
    if choice3 == 1: 
        print("you have selected sedan")
    elif choice3 == 2:
        print("you have selected XUV")
    else:
        print("Wrong choice")
else:
    print("invalid input")
    