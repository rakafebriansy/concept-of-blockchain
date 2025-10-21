import sys, hashlib, json
from time import time
from uuid import uuid4
from flask import Flask
from flask.globals import request
from flask.json import jsonify
from urllib.parse import urlparse

class Blockchain(object):
    difficulty_target = "0000" # Define the difficulty target for proof of work

    def __init__(self):
        self.chain = [] # Initialize the blockchain
        self.current_transactions = [] # Initialize the list of current transactions

        genesis_hashed = self.hash_block('genesis_block') # Create the genesis block

        self.append_block(previous_hash=genesis_hashed, nonce=self.proof_of_work(0, genesis_hashed, [])) # Append the genesis block to the chain
    
    def hash_block(self, block):
        block_string = json.dumps(block, sort_keys=True).encode() # Encode the block
        return hashlib.sha256(block_string).hexdigest() # Return the SHA-256 hash of the block

    def proof_of_work(self, index, previous_hash, transactions):
        nonce = 0 # Start nonce at 0
        
        while self.valid_proof(index, previous_hash, transactions, nonce) is False: # Loop until a valid proof is found
            nonce += 1 # Increment nonce
        return nonce # Return the valid nonce

    def valid_proof(self, index, previous_hash, transactions, nonce):
        guess = f'{index}{previous_hash}{transactions}{nonce}'.encode() # Create the guess string
        guess_hash = hashlib.sha256(guess).hexdigest() # Hash the guess
        return guess_hash[:len(self.difficulty_target)] == self.difficulty_target # Check if the hash meets the difficulty target
    
    def append_block(self, nonce, previous_hash=None):
        block = {
            'index': len(self.chain) + 1, # Set the block index
            'timestamp': time(), # Set the block timestamp
            'transactions': self.current_transactions, # Set the block transactions
            'nonce': nonce, # Set the block nonce
            'previous_hash': previous_hash or self.hash_block(self.chain[-1]), # Set the previous hash or hash of the last block
        } # Create a new block

        self.current_transactions = [] # Reset the current list of transactions
        self.chain.append(block) # Append the new block to the chain
        return block # Return the new block
        
    def add_transaction(self, sender, recipient, amount):
        self.current_transactions.append({
            'sender': sender, # Set the sender
            'recipient': recipient, # Set the recipient
            'amount': amount, # Set the amount
        }) # Append the new transaction to the list of current transactions
        return self.last_block['index'] + 1 # Return the index of the block that will hold this transaction
    
    @property
    def last_block(self):
        return self.chain[-1] # Return the last block in the chain

app = Flask(__name__) # Create a Flask app
node_identifier = str(uuid4()).replace('-', '') # Generate a unique identifier for this node
blockchain = Blockchain() # Create a new Blockchain instance

# routes
@app.route('/blockchain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain, # Return the full blockchain
        'length': len(blockchain.chain), # Return the length of the blockchain
    }
    
    return jsonify(response), 200 # Return the response as JSON with status code 200

@app.route('/mine', methods=['GET'])
def mine_block():
    blockchain.add_transaction(
        sender="0", # The sender is "0" meaning the system (a mining reward)
        recipient=node_identifier, # The recipient is the node that mined the block, and the reward amount is 1
        amount=1
    ) # Add a new transaction to the blockchain.

    last_block_hash = blockchain.hash_block(blockchain.last_block) # Get the hash of the last block in the blockchain
    index = len(blockchain.chain) # Determine the index of the next block to be mined
    nonce = blockchain.proof_of_work(index, last_block_hash, blockchain.current_transactions) # Perform the proof of work algorithm to find a valid nonce
    block = blockchain.append_block(nonce, last_block_hash) # Once a valid nonce is found, append (add) the new block to the blockchain
    
    response = {
        'message': "Block successfully added (mined)",
        'index': block['index'], # Index of the newly mined block
        'previous_hash': block['previous_hash'], # Hash of the previous block
        'nonce': block['nonce'], # Nonce value found during mining
        'transactions': block['transactions'], # List of transactions included in the block
    }    

    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transactions():
    values = request.get_json() # Extract the JSON data from the request body

    required_fields = ['sender','recipient','amount'] # Define the required fields for a transaction
    if not all(k in values for k in required_fields):
        return ('Missing fields', 400) # If any required field is missing, return an error 400 (Bad Request)
    
    index = blockchain.add_transaction(
        values['sender'], # Sender address
        values['recipient'], # Recipient address
        values['amount'], # Transaction amount
    ) # Add the new transaction to the list of current (unconfirmed) transactions

    response = {
        'message': f"Transaction will be added into {index} block" # Prepare a response indicating which block the transaction will be added to
    }

    return jsonify(response), 201

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(sys.argv[1]))