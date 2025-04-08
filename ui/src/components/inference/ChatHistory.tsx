import React, { useEffect, useState } from 'react';
import axiosBE from '../../http/axiosConfig';
import { Paper, Typography, List, ListItem, ListItemButton, ListItemText, ListItemIcon, Divider, Box, ListItemSecondaryAction, IconButton, Dialog, DialogActions, DialogContent, DialogTitle, Button, TextField } from '@mui/material';
import MessageIcon from '@mui/icons-material/Message';
import HistoryIcon from '@mui/icons-material/History';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import moment from 'moment';
import { ConfirmationModal } from '../shared/ConfirmationModal';

interface ChatMessage {
  id: string;
  text: string;
  sender: 'user' | 'bot';
}

interface ChatHistoryProps {
  modelId: string;
  isStreaming: boolean;
  onChatSelect: (chatId: string, messages: ChatMessage[]) => void;
  currentSessionId: string;
  historyChats: HistoryChat[];
  setHistoryChats: (historyChats: HistoryChat[]) => void;
  clearChat: (sessionId: string) => void;
  unloadingModel: boolean;
}

export interface HistoryChat {
  sessionId: string;
  latestTimestamp: string;
  messages: ChatMessage[];
  firstMessage: string;
  title?: string;
}

const ChatHistory: React.FC<ChatHistoryProps> = ({ modelId, isStreaming, onChatSelect, currentSessionId, historyChats, setHistoryChats, clearChat, unloadingModel }) => {
  const [deleteConfirmationModal, setDeleteConfirmationModal] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [selectedTitle, setSelectedTitle] = useState<string | null>(null);
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [tempTitle, setTempTitle] = useState<string | null>(null);

  const deleteSession = async (sessionId: string) => {
    try {
      const response = await axiosBE.post('/api/chat/deleteSession', {sessionId: selectedSessionId});
      setHistoryChats(historyChats.filter((chat) => chat.sessionId !== sessionId));                   
      if (sessionId === currentSessionId) {
        clearChat(sessionId);
      }
      setDeleteConfirmationModal(false); 
    } catch (error) {
      console.error('Error deleting session:', error);
    }
  };

  const handleDeleteClick = (sessionId: string, firstMessage: string) => {
    setSelectedSessionId(sessionId);
    setSelectedTitle(firstMessage);
    setDeleteConfirmationModal(true); 
  };

  const handleCloseDeleteModal = () => {
    setDeleteConfirmationModal(false);
    setSelectedSessionId(null); 
    setSelectedTitle(null); 
  };

  const handleEditStart = (sessionId: string, currentTitle: string) => {
    setEditingSessionId(sessionId);
    setTempTitle(currentTitle);
  };

  const handleEditCancel = () => {
    setEditingSessionId(null);
    setTempTitle(null);
  };

  const handleEditSave = async () => {
    if (editingSessionId && tempTitle) {
      try {
        await axiosBE.post('/api/chat/renameSession', { sessionId: editingSessionId, title: tempTitle });
        const updatedChats = historyChats.map((chat) =>
          chat.sessionId === editingSessionId ? { ...chat, title: tempTitle } : chat
        );
        setHistoryChats(updatedChats);
      } catch (error) {
        console.error('Error renaming session:', error);
      } finally {
        setEditingSessionId(null);
        setTempTitle(null);
      }
    }
  };

  const handleDeleteConfirm = () => {
    if (selectedSessionId) { 
      deleteSession(selectedSessionId);
    }
  }

  return (
    <Paper elevation={3} sx={{ width: '95%', marginTop: '10px', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <HistoryIcon /> Chat History
        </Typography>
      </Box>

      <List sx={{ overflow: 'auto', flexGrow: 1 }}>
        {historyChats.map((chat, index) => (
          <React.Fragment key={index}>
            <ListItem disablePadding>
              <ListItemButton
                className={`custom-list-item-button ${editingSessionId === chat.sessionId ? 'editing' : ''}`}
                selected={currentSessionId === chat.sessionId}
                disabled={isStreaming}
                onClick={() => onChatSelect(chat.sessionId, chat.messages)}
              >
                <ListItemIcon>
                  <MessageIcon />
                </ListItemIcon>
                <ListItemText
                  primary={
                    editingSessionId === chat.sessionId ? (
                      <TextField
                        className='text-field-rename'
                        value={tempTitle || ''}
                        onChange={(e) => setTempTitle(e.target.value)}
                        onBlur={() => handleEditCancel()} 
                        onKeyDown={(e) => {if (e.key === 'Enter') {handleEditSave()}
                                          else if (e.key === 'Escape') {handleEditCancel()}}}
                        autoFocus
                        size="small"
                        variant="outlined"
                        inputProps={{ maxLength: 60 }}
                        helperText={`${tempTitle?.length || 0}/60 characters`}
                        fullWidth
                        FormHelperTextProps={{
                          sx: { marginLeft: 0, marginTop: '4px', fontSize: '0.75rem' },
                        }}
                      /> ) : (
                      <React.Fragment>
                        {chat.title ? chat.title : chat.firstMessage}
                        <IconButton
                          title="Rename session"
                          edge="end"
                          aria-label="edit"
                          onClick={() => handleEditStart(chat.sessionId, chat.title || chat.firstMessage)}
                        >
                          <EditIcon fontSize="small" sx={{height: '15px'}}/>
                        </IconButton>
                      </React.Fragment>)}
                  secondary={
                    <Typography component="span" variant="caption" color="text.secondary">
                      {moment(chat.latestTimestamp).format('DD/MM/YYYY HH:mm:ss')}
                    </Typography>}
                />
              </ListItemButton>
              <ListItemSecondaryAction>
                <IconButton
                  title="Delete session"
                  edge="end"
                  aria-label="delete"
                  onClick={() => handleDeleteClick(chat.sessionId, chat.title || chat.firstMessage)}
                >
                  <DeleteIcon />
                </IconButton>
              </ListItemSecondaryAction>
            </ListItem>
            {index < historyChats.length - 1 && <Divider />}
          </React.Fragment>
        ))}
        {historyChats.length === 0 && (
          <ListItem>
            <ListItemText
              primary="No chat history yet"
              sx={{ textAlign: 'center', color: 'text.secondary' }}
            />
          </ListItem>
        )}
      </List>

      {/* Delete confirmation Modal */}
      <ConfirmationModal text={`Are you sure you want to delete this chat: ${selectedTitle}?`} open={deleteConfirmationModal} onClose={handleCloseDeleteModal} handleClick={handleDeleteConfirm}/>
      
    </Paper>
  );
};

export default ChatHistory;
