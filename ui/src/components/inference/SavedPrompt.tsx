import React, { useState, useEffect } from 'react';
import { useTable, useSortBy, Column } from 'react-table';
import { IconButton, Modal, Box, Typography, Table, TableHead, TableRow, TableCell, TableSortLabel, TableBody } from '@mui/material';
import { FaFileAlt, FaEdit, FaTrash } from 'react-icons/fa';
import axios from '../../http/axiosConfig';
import { Light as SyntaxHighlighter } from 'react-syntax-highlighter';
import python from 'react-syntax-highlighter/dist/esm/languages/hljs/python';
import { atomOneDark } from 'react-syntax-highlighter/dist/esm/styles/hljs';
import ReactQuill from 'react-quill';
import 'react-quill/dist/quill.snow.css'; // Import Quill styles
import '../../styles.css';
import { ConfirmationModal } from '../shared/ConfirmationModal';

// Register the language
SyntaxHighlighter.registerLanguage('python', python);

interface SavedPromptData {
  modelId: string;
  modelName: string;
  uniqueId: string;
  trainingName: string;
  promptText: string;
  promptUserLatestText: string;
  promptLLMLatestText: string;
  promptName?: string;
  comment: string;
  completed: boolean;
  delete: void;
}

interface CodeSectionProps {
  title: string;
  content: string;
}

const CodeSection: React.FC<CodeSectionProps> = ({ title, content }) => (
  <div>
    <Typography variant="h6" style={{ fontFamily: "ui-monospace" }} gutterBottom>
      {title}
    </Typography>
    <SyntaxHighlighter className="code-visualizer" language="python" style={atomOneDark}>
      {content || ''}
    </SyntaxHighlighter>
  </div>
);

const SavedPrompts: React.FC = () => {
  const [data, setData] = useState<SavedPromptData[]>([]);
  const [open, setOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [commentData, setCommentData] = useState<{ modelId: string, uniqueId: String, comment: string } | null>(null);
  const [selectedPrompt, setSelectedPrompt] = useState<string | null>(null);
  const [questionPart, setQuestionPart] = useState<string>(''); // Include the '*** Settings ***:' in the question part
  const [answerPart, setAnswerPart] = useState<string>(''); // Start after '*** Settings ***:' for the answer part
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [promptToDelete, setPromptToDelete] = useState<{ modelId: string, uniqueId: string, promptName: string } | null>(null);

  const columns: Column<SavedPromptData>[] = React.useMemo(
    () => [
      {
        Header: 'Prompt Name',
        accessor: (row: SavedPromptData) => row.promptName || row.trainingName // Use promptName if it exists, otherwise trainingName
      },
      {
        Header: 'Prompt Text',
        accessor: 'promptText',
        Cell: ({ row }: any) => (
          <IconButton onClick={() => handleOpen(row.original.promptUserLatestText, row.original.promptLLMLatestText, row.original.promptText)}>
            <FaFileAlt />
          </IconButton>
        ),
      },
      {
        Header: 'Model Name',
        accessor: (row: SavedPromptData) => row.modelName || "N/A"
      },
      {
        Header: 'Comment',
        accessor: 'comment',
        Cell: ({ row }: any) => (
          <>
            <IconButton onClick={() => handleEditOpen(row.original)}>
              <FaEdit />
            </IconButton>
          </>
        ),
      },
      {
        Header: 'Completed',
        accessor: 'completed',
        Cell: ({ row }: any) => (
          <input
            type="checkbox"
            checked={row.original.completed || false} // Assuming `completed` is a boolean in your data
            onChange={(e) => handleCompletedChange(row.original.modelId, row.original.uniqueId, e.target.checked)}
          />
        ),
      },
      {
        Header: 'Delete',
        accessor: 'delete',
        Cell: ({ row }: any) => (
          <IconButton onClick={() => handleDeleteOpen(row.original.modelId, row.original.uniqueId, row.original.promptName)}>
            <FaTrash />
          </IconButton>
        ),
      },
    ],
    []
  );

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get('/api/prompts/retrievePrompt');
        setData(response.data.result);
      } catch (error) {
        console.error('Error fetching saved prompts:', error);
      }
    };

    fetchData();
  }, []);

  // const handleOpen = (promptText: string) => {
  //   setSelectedPrompt(promptText);

  //   // Find the index of either '[/INST]' or '<|eot_id|>'
  //   const endIndexInst = promptText.indexOf('[/INST]');
  //   const endIndexEot = promptText.indexOf('<|start_header_id|>assistant<|end_header_id|>');

  //   // Determine which marker is present
  //   const endIndex = endIndexInst !== -1 ? endIndexInst : endIndexEot;

  //   // If a marker is found, split the promptText
  //   if (endIndex !== -1) {
  //     const markerLength = endIndexInst !== -1 ? '[/INST]'.length : '<|start_header_id|>assistant<|end_header_id|>'.length;
  //     // Include the marker in the question part
  //     setQuestionPart(promptText.substring(0, endIndex + markerLength));
  //     // Answer part starts after the marker
  //     setAnswerPart(promptText.substring(endIndex + markerLength));
  //   } else {
  //     // Handle case where neither marker is found
  //     setQuestionPart(promptText);  // Use the whole text as the question
  //     setAnswerPart('');            // No answer part if no marker is found
  //   }    
  //   // const settingsIndex = promptText.indexOf('*** Settings ***:');
  //   // setQuestionPart(promptText.substring(0, settingsIndex + 17))
  //   // setAnswerPart(promptText.substring(settingsIndex + 17))
  //   setOpen(true);
  // };

  const handleOpen = (userLatestQuestion: string, llmLatestAnswer: string, entireText: string) => {
    setSelectedPrompt(entireText);
    setQuestionPart(userLatestQuestion);
    setAnswerPart(llmLatestAnswer);
    setOpen(true);
  }

  const handleClose = () => {
    setOpen(false);
    setSelectedPrompt(null);
  };

  const handleEditOpen = (row: SavedPromptData) => {
    setCommentData({ modelId: row.modelId, uniqueId: row.uniqueId, comment: row.comment });
    setEditOpen(true);
  };

  const handleEditClose = () => {
    setEditOpen(false);
    setCommentData(null);
  };

  const handleSaveComment = async () => {
    if (commentData) {
      try {
        await axios.post('/api/prompts/savePromptComment', { modelId: commentData.modelId, uniqueId: commentData.uniqueId, comment: commentData.comment });
        // Update the data state with the new comment
        setData(prevData =>
          prevData.map(item => item.modelId === commentData.modelId && item.uniqueId === commentData.uniqueId ? { ...item, comment: commentData.comment } : item)
        );
        handleEditClose();
      } catch (error) {
        console.error('Error saving comment:', error);
      }
    }
  };

  const handleCompletedChange = async (modelId: string, uniqueId: string, completed: boolean) => {
    try {
      await axios.post('/api/prompts/markPromptAsComplete', {
        modelId,
        uniqueId,
        completed
      });

      // Update the state after successful API call
      setData(prevData =>
        prevData.map(item => item.modelId === modelId && item.uniqueId === uniqueId ? { ...item, completed } : item)
      );
    } catch (error) {
      console.error('Error marking prompt as complete:', error);
    }
  };

  const handleDeleteOpen = (modelId: string, uniqueId: string, promptName: string) => {
    setPromptToDelete({ modelId, uniqueId, promptName });
    setDeleteModalOpen(true);
  };
  
  const handleDeleteClose = () => {
    setDeleteModalOpen(false);
    setPromptToDelete(null);
  };
  
  const handleDeleteConfirm = async () => {
    if (promptToDelete) {
      try {
        await axios.post('/api/prompts/deletePrompt', {
          uniqueId: promptToDelete.uniqueId
        });
        
        // Update the state to remove the deleted prompt
        setData(prevData => 
          prevData.filter(item => item.uniqueId !== promptToDelete.uniqueId)
        );
        handleDeleteClose();
      } catch (error) {
        console.error('Error deleting prompt:', error);
      }
    }
  };

  const { getTableProps, getTableBodyProps, headerGroups, rows, prepareRow } = useTable(
    { columns, data },
    useSortBy
  );

  return (
    <div className="table-container">
      <h2>Saved Prompts</h2>
      <Table {...getTableProps()} className="forms-table">
        <TableHead>
          {headerGroups.map(headerGroup => (
            <TableRow {...headerGroup.getHeaderGroupProps()}>
              {headerGroup.headers.map((column: any) => (
                <TableCell {...column.getHeaderProps(column.getSortByToggleProps())} sx={{ borderRight: '1px solid #ddd' }}>
                  <TableSortLabel
                    active={column.isSorted}
                    direction={column.isSortedDesc ? 'desc' : 'asc'}
                  >
                    {column.render('Header')}
                  </TableSortLabel>
                  <span>
                    {column.isSorted
                      ? column.isSortedDesc
                        ? ' 🔽'
                        : ' 🔼'
                      : ''}
                  </span>
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableHead>
        <TableBody {...getTableBodyProps()}>
          {rows.map(row => {
            prepareRow(row);
            return (
              <TableRow {...row.getRowProps()}>
                {row.cells.map(cell => (
                  <TableCell {...cell.getCellProps()} className="table-cell" sx={{ borderRight: '1px solid #ddd' }}>
                    {cell.render('Cell')}
                  </TableCell>
                ))}
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
      <Modal open={open} onClose={handleClose}>
        <Box
          sx={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            width: 800,
            bgcolor: 'background.paper',
            border: '2px solid #000',
            boxShadow: 24,
            overflowY: 'auto',
            overflowX: 'hidden',
            maxWidth: '80%',
            maxHeight: '80%',
            p: 4,
          }}
        >
          <div >
            <CodeSection title="User Question" content={questionPart} />
            <CodeSection title="LLM Answer" content={answerPart} />
            <CodeSection title="Entire Chat" content={selectedPrompt || ''} />
          </div>
        </Box>
      </Modal>
      <Modal open={editOpen} onClose={handleEditClose}>
        <Box
          sx={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            width: 800,
            bgcolor: 'background.paper',
            border: '2px solid #000',
            boxShadow: 24,
            p: 4,
          }}
        >
          <ReactQuill value={commentData?.comment || ''} onChange={(value: string) => setCommentData({ ...commentData, comment: value, modelId: commentData?.modelId || '', uniqueId: commentData?.uniqueId || '' })} />
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
            <button onClick={handleEditClose}>Cancel</button>
            <button onClick={handleSaveComment} style={{ marginLeft: 8 }}>Save</button>
          </Box>
        </Box>
      </Modal>
      <ConfirmationModal text={`Are you sure you want to delete '${promptToDelete?.promptName}' prompt?`} open={deleteModalOpen} onClose={handleDeleteClose} handleClick={handleDeleteConfirm}/>
    </div>
  );
};

export default SavedPrompts;
