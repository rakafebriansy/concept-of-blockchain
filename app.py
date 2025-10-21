import sys, hashlib, json, requests
from time import time
from uuid import uuid4
from flask import Flask
from flask.globals import request
from flask.json import jsonify
from urllib.parse import urlparse

class Blockchain(object):
    difficulty_target = "0000" # Define the difficulty target for proof of work

    def __init__(self):
        self.nodes = set() # Store a list of connected nodes (peers)
        self.chain = [] # Initialize the blockchain
        self.current_transactions = [] # Initialize the list of current transactions

        genesis_hashed = self.hash_block('genesis_block') # Create the genesis block

        self.append_block(
            previous_hash=genesis_hashed, 
            nonce=self.proof_of_work(0, genesis_hashed, [])
        ) # Append the genesis block to the chain
    
    def add_node(self, address):
        parsed_url = urlparse(address) # Parse the given address (e.g., 'http://127.0.0.1:5001') to extract components
        self.nodes.add(parsed_url.netloc) # Add the network location (host:port) to the set of known nodes

    def valid_chain(self, chain):
        last_block = chain[0] # Start validation from the first block in the provided chain
        current_index = 1 # Start from the second block

        while current_index < len(chain): # Iterate through all remaining blocks in the chain
            block = chain[current_index] # Get the current block being validated

            if block['previous_hash'] != self.hash_block(last_block): # Check if the current block's 'previous_hash' matches the hash of the previous block
                return False # If mismatch, the chain is invalid
            
            if not self.valid_proof(
                current_index,  # Index of the current block
                block['previous_hash'],  # Hash of the previous block
                json.dumps(block['transactions'], sort_keys=True),  # Sort transactions before hashing for consistency
                block['nonce'] # Nonce value used for mining
                ): # Verify the proof of work (validate that the nonce produces a valid hash)
                return False # If the proof of work is invalid, reject the chain
            
            last_block = block # Move to the next block
            current_index += 1 # Increment index

        return True # If all blocks are valid, return True

    def update_blockchain(self):
        neighbors = self.nodes # Get the list of neighboring nodes in the network
        new_chain = None # Temporary variable to store a potentially longer valid chain

        max_length = len(self.chain) # Store the length of the current blockchain

        for node in neighbors: # Iterate through all known nodes
            try:
                response = requests.get(f'http://{node}/blockchain') # Request the blockchain from the neighbor node

                if response.status_code == 200: # Check if the node responded successfully
                    decoded_response = response.json() # Parse the JSON response

                    if decoded_response['length'] > max_length and self.valid_chain(decoded_response['chain']): # Compare lengths and check if the neighbor's chain is valid
                        # If a longer and valid chain is found, store it
                        max_length = decoded_response['length']
                        new_chain = decoded_response['chain']

            except requests.exceptions.RequestException as e: # If a node cannot be reached
                print(f"Failed to connect to node {node}: {e}")

        if new_chain: # If a longer valid chain was found
            self.chain = new_chain # Replace the current chain with it
            return True # Blockchain was updated

        return False # If no longer valid chain found, keep the current one

    def hash_block(self, block):
        block_string = json.dumps(block, sort_keys=True).encode() # Encode the block
        return hashlib.sha256(block_string).hexdigest() # Return the SHA-256 hash of the block

    def proof_of_work(self, index, previous_hash, transactions):
        nonce = 0 # Start nonce at 0
        tx_string = json.dumps(transactions, sort_keys=True) # Hash the transactions to avoid the change of dict keys

        while self.valid_proof(index, previous_hash, tx_string, nonce) is False: # Loop until a valid proof is found
            nonce += 1 # Increment nonce
        return nonce # Return the valid nonce

    def valid_proof(self, index, previous_hash, tx_string, nonce):
        guess = f'{index}{previous_hash}{tx_string}{nonce}'.encode() # Create the guess string
        guess_hash = hashlib.sha256(guess).hexdigest() # Hash the guess
        return guess_hash[:len(self.difficulty_target)] == self.difficulty_target # Check if the hash meets the difficulty target
    
    def append_block(self, nonce, timestamp = None, previous_hash=None):
        block = {
            'index': len(self.chain), # Set the block index
            'timestamp': timestamp or time(), # Set the block timestamp
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
    if not all(k in values for k in required_fields): # If any required field is missing
        return ('Missing fields', 400) # Return an error 400 (Bad Request)
    
    index = blockchain.add_transaction(
        values['sender'], # Sender address
        values['recipient'], # Recipient address
        values['amount'], # Transaction amount
    ) # Add the new transaction to the list of current (unconfirmed) transactions

    response = {
        'message': f"Transaction will be added into {index} block" # Prepare a response indicating which block the transaction will be added to
    }

    return jsonify(response), 201

@app.route('/nodes/add', methods=['POST'])
def add_node():
    values = request.get_json()
    nodes = values.get('nodes')

    if nodes is None:
        return ('Error, missing node(s) info', 400)
    
    for node in nodes:
        blockchain.add_node(node)
    
    response = {
        'message': 'New node has beed added',
        'nodes': list(blockchain.nodes)
    }

    return jsonify(response), 201

@app.route('/nodes/sync', methods=['GET'])
def sync_nodes():
    updated = blockchain.update_blockchain()
    if updated:
        response = {
            'message': 'Blockchain has beed updated',
            'blockchain': blockchain.chain
        }
    else:
        response = {
            'message': 'Blockchain is already up to date',
            'blockchain': blockchain.chain
        }
                
    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(sys.argv[1]))