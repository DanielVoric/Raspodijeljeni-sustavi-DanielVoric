from pymongo import MongoClient


MONGODB_URI = "mongodb+srv://dvoric_db_user:wAwEVVsuJdBQmCh3@akcijosc.1qsh5j4.mongodb.net/?retryWrites=true&w=majority&appName=AkcijoSC"


client = MongoClient(
	MONGODB_URI,
	serverSelectionTimeoutMS=5000,
	tls=True,
)
db = client["baza_artikli"] 
artikli = db["artikli"]     


