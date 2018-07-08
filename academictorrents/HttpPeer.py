import requests
from pubsub import pub
from collections import defaultdict


class HttpPeer(object):
    def __init__(self, torrent, url):
        self.readBuffer = b""
        self.torrent = torrent
        self.handshake(url)

    def handshake(self, url):
        if not url:
            raise Exception
        resp = requests.head(url)
        if resp.headers.get('Accept-Ranges', False) and resp.headers.get('ETag', False):  # if it was a full-url
            self.url = '/'.join(url.split('/')[0:-1]) + '/'
            self.etag = resp.headers.get('etag', None)
        elif url[-1] == '/':  # maybe we need to construct a full-url
            directory = self.torrent.torrentFile.get('info', {}).get('name')
            some_filename = self.torrent.torrentFile.get('info', {}).get('files', [{'path': ['']}])[0].get('path')[0]
            compound_url = url + directory + '/' + some_filename
            resp = requests.head(compound_url)
            if resp.headers.get('Accept-Ranges', False) and resp.headers.get('ETag', False):  # if it wasn't a full-url
                self.url = url + directory + '/'
                self.etag = resp.headers.get('etag', None)
            else:
                raise Exception

    def get_pieces(self, piecesManager):
        # TODO: Add another way to exit this loop when we don't hit the max size
        size = 0
        temp_size = 0
        max_size_to_download = 1500000
        temp_pieces = []
        pieces = []
        for idx, b in enumerate(piecesManager.bitfield):
            piece = piecesManager.pieces[idx]
            if not b and not piece.finished:
                temp_pieces.append(piece)
                temp_size += piece.pieceSize

            if size < temp_size:
                size = temp_size
                pieces = temp_pieces

            if size > max_size_to_download or len(pieces) > 5:
                return pieces

            if b:
                temp_pieces = []
                temp_size = 0
        return pieces

    def request_ranges(self, pieces_by_file):
        responses = {}
        for filename, pieces in pieces_by_file.items():
            start = pieces[0].get_file_offset(filename)
            directory = self.torrent.torrentFile.get('name')
            end = start
            for piece in pieces:
                end += piece.get_file_length(filename)
            resp = requests.get(self.url + filename, headers={'Range': 'bytes=' + str(start) + '-' + str(end)})
            responses[filename] = (resp, start)
        return responses

    def publish_responses(self, responses, pieces_by_file):
        unique_pieces = set()
        for piece_list in pieces_by_file.values():
            for piece in piece_list:
                unique_pieces.add(piece)

        for piece in unique_pieces:
            if piece.finished:
                continue
            for f in piece.files:
                filename = f.get('path').split('/')[-1]
                resp = responses[filename][0]
                resp_start = responses[filename][1]
                length = piece.get_file_length(filename)
                pieceOffset = piece.get_piece_offset(filename)
                fileOffset = piece.get_file_offset(filename) - resp_start
                piece.pieceData += resp.content[fileOffset: fileOffset + length]

            blockOffset = 0
            try:
                for idx in range(int(len(piece.pieceData)/piece.BLOCK_SIZE)):
                    block_size = piece.blocks[idx][1]
                    pub.sendMessage('PiecesManager.Piece', piece=(piece.pieceIndex, blockOffset, piece.pieceData[blockOffset: blockOffset + block_size]))
                    blockOffset += block_size
            except Exception:
                pass

    def construct_pieces_by_file(self, pieces):
        pieces_by_file = defaultdict(list)
        for piece in pieces:
            for f in piece.files:
                filename = f.get('path').split('/')[-1]
                pieces_by_file[filename].append(piece)
        return pieces_by_file
