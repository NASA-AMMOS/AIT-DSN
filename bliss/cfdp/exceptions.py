class InvalidTransaction(Exception):
     def __init__(self, transaction_id):
         self.id = transaction_id
         self.message = "Invalid transaction ID {}".format(transaction_id)
