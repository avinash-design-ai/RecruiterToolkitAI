class ParserManager:

    def __init__(self, blocks):

        self.blocks = blocks

        self.claimed = set()

    # ---------------------------------

    def claim(self, indexes):

        self.claimed.update(indexes)

    # ---------------------------------

    def is_claimed(self, index):

        return index in self.claimed

    # ---------------------------------

    def available(self):

        return [

            (i, block)

            for i, block in enumerate(self.blocks)

            if i not in self.claimed

        ]

    # ---------------------------------

    def get_blocks(self):

        return [

            block

            for i, block in self.available()

        ]

    # ---------------------------------

    def get_indexes(self):

        return [

            i

            for i, block in self.available()

        ]
