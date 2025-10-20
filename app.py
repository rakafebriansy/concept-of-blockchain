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
        self.chain = [] # Initialize the blockchain
        self.current_transactions = [] # Initialize the list of current transactions

        genesis_hashed = self.hash_block('genesis_block') # Create the genesis block

        self.append_block(previous_hash=genesis_hashed, nonce=self.proof_of_work(0, genesis_hashed, [])) # Append the genesis block to the chain
    
    def hash_block(self, block):
        block_string = json.dumps(block, sort_keys=True).encode() # Encode the block
        return hashlib.sha256(block_string).hexdigest() # Return the SHA-256 hash of the block

    def proof_of_work(self, index, previous_hash, transactions, last_nonce):
        nonce = 0 # Start nonce at 0
        while self.valid_proof(index, previous_hash, transactions, last_nonce) is False: # Loop until a valid proof is found
            nonce += 1 # Increment nonce
        return nonce # Return the valid nonce

    def valid_proof(self, index, previous_hash, transactions, last_nonce):
        guess = f'{index}{previous_hash}{transactions}{last_nonce}'.encode() # Create the guess string
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

blockchain = Blockchain() # Create a new Blockchain instance