import React, { useCallback, useEffect, useState, useRef, useMemo, forwardRef, useImperativeHandle } from 'react';
import { EditorContent } from '@tiptap/react';
import { Editor } from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import Mention from '@tiptap/extension-mention';
import { SuggestionProps } from '@tiptap/suggestion';
import tippy from 'tippy.js';
import 'tippy.js/dist/tippy.css';
import IconButton from '@mui/material/IconButton';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import axiosBE from '../../http/axiosConfig';
import qs from 'qs';

interface MentionItem {
  id: string;
  name: string;
  file_location: string;
  git_repo_link: string;
  element_type: string;
  code: string;
}

interface MessageInputWithMentionsProps {
  placeholder?: string;
  onSend: (msg: string) => void;
  disabled?: boolean;
  attachButton?: boolean;
  gitReposLink: string[];
}

const insertMentionCode = (
  item: MentionItem,
  command: (item: any) => void,
  props: SuggestionProps,
  view: Editor['view']
) => {
  if (item.id === '__none__') return;

  if (view && props.range) {
    const { state, dispatch } = view;
    dispatch(state.tr.delete(props.range.from, props.range.to));
  }

  command({
    id: item.id,
    name: item.code,
    label: item.code,
    element_type: item.element_type,
  });
};

const getIconForType = (type: string): string => {
  switch (type.toLowerCase()) {
    case 'function':
      return 'ƒ';
    case 'file':
      return '📄';
    case 'class':
      return '🏛️';
    case 'test':
      return '🧪';
    case 'test case':
      return '📝';
    default:
      return '📌';
  }
};

export interface MessageInputWithMentionsRef {
  clearInput: () => void;
}
const MessageInputWithMentions = forwardRef<MessageInputWithMentionsRef, MessageInputWithMentionsProps>(
  ({ placeholder = 'Type your message here...', onSend, disabled = false, attachButton = true, gitReposLink }, ref) => {
    
  const mentionActiveRef = useRef(false);
  const [mentionableElements, setMentionableElements] = useState<MentionItem[]>([]);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [selectedMentions, setSelectedMentions] = useState<MentionItem[]>([]);
  const [isMentionLoaded, setIsMentionLoaded] = useState(false);


  useEffect(() => {
    const fetchMentionableElements = async () => {
      try {
        const response = await axiosBE.get('/api/parser/parsedElements', {
          params: { gitReposLink: gitReposLink },
          paramsSerializer: params => qs.stringify(params, { arrayFormat: 'repeat' })
        });
        const elements = response.data?.data || [];
        const formatted = elements.map((el: any) => ({
          id: el.uuid || el._id,
          name: el.name,
          code: el.code,
          git_repo_link: el.git_repo_link || 'Other',
          file_location: el.file_location || '',
          element_type: el.element_type || '',
        }));
        setMentionableElements(formatted);
      } catch (error) {
        console.error('Failed to fetch mentionable users:', error);
      } finally {
        setIsMentionLoaded(true);
      }
    };
    fetchMentionableElements();
  }, []);

  useEffect(() => {
    const style = document.createElement('style');
    style.textContent = `
          .tippy-box[data-theme~='light'] {
            background-color: #fff;
            color: #000;
            border-radius: 0.75rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            padding: 0;
            min-width: 720px;       
            max-width: 95vw;         
          }

          .tippy-box[data-theme~='light'] .tippy-arrow {
            display: none !important;
          }

          span[data-mention] {
            display: inline;
            background-color: #e0f7fa;
            padding: 2px 4px;
            border-radius: 4px;
            color: #00796b;
            white-space: nowrap;
          }

          .mention-dropdown {
            display: flex;
            flex-direction: column;
            padding: 0.4rem;
            max-height: 320px;
            overflow-y: auto;
            width: 100%;            
            min-width: 720px;          
            max-width: 95vw;
          }

          .mention-group-header {
            font-weight: bold;
            padding: 8px 12px;
            background-color: #f0f0f0;
            cursor: pointer;
          }

          .mention-button {
            all: unset;
            display: flex;
            align-items: center;
            width: 100%;
            padding: 12px 16px;
            /* Increased padding */
            border-radius: 8px;
            /* Slightly rounder */
            cursor: pointer;
            font-size: 1rem;
            /* Slightly larger text */
            box-sizing: border-box;
            gap: 8px;
             max-width: 100%; 
          }

          .mention-button:hover {
            background-color: #f5f5f5;
          }

          .mention-type {
            color: #888;
            margin-left: auto;
          }

          .tiptap:focus {
            outline: none !important;
            box-shadow: none !important;
          }

          .mention-button.is-selected {
            background-color: #e0f7fa;
          }

          .chat-bubble-content {
            max-height: 250px;
            overflow-y: auto;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-word;
            border-radius: 1rem;
            padding: 1rem;
            background: #f0f8f8;
            color: #333;
            font-size: 0.95rem;
            line-height: 1.4;
            position: relative;
          }
    `;

    document.head.appendChild(style);
    return () => {
      document.head.removeChild(style);
    };
  }, []);

  useEffect(() => {
    if (editor || !isMentionLoaded) return;

    const newEditor = new Editor({
      extensions: [
        StarterKit,
        Mention.configure({
          HTMLAttributes: {
            style: 'background-color: #E0F7FA; color: #00796B; border-radius: 4px; padding: 1px 4px;',
          },
          renderLabel({ node }) {
            return `@${node.attrs.name || node.attrs.label || node.attrs.id}`;
          },
          suggestion: {
            char: '@',

            items: ({ query }) => {
              if (mentionableElements.length === 0) return [];

              return mentionableElements.filter(item =>
                item.name.toLowerCase().includes(query.toLowerCase()) ||
                item.code.toLowerCase().includes(query.toLowerCase()) ||
                item.file_location.toLowerCase().includes(query.toLowerCase())
              );
            },

            render: () => {
              let popup: any;
              let component: HTMLDivElement;
              let selectedIndex = 0;
              let currentItems: MentionItem[] = [];
              let currentCommand: (item: any) => void;
              const expandedGroups = new Set<string>();
              let currentProps: SuggestionProps;

              const createGroupHeader = (repo: string) => {
                const header = document.createElement('div');
                header.className = 'mention-group-header';
                header.textContent = repo;
                header.addEventListener('click', () => {
                  if (expandedGroups.has(repo)) {
                    expandedGroups.delete(repo);
                  } else {
                    expandedGroups.add(repo);
                  }
                  updateSelection();
                });
                return header;
              };

              const createMentionButton = (
                item: MentionItem,
                command: (item: any) => void,
                props: SuggestionProps,
                isSelected = false
              ) => {
                const button = document.createElement('button');
                button.className = 'mention-button';
                if (isSelected) button.classList.add('is-selected');
                if (item.id === '__none__') {
                  button.style.opacity = '0.6';
                  button.style.cursor = 'default';
                }

                const nameSpan = document.createElement('span');
                nameSpan.textContent = item.name;

                const locationRow = document.createElement('div');
                locationRow.textContent = item.file_location || '';
                locationRow.style.fontSize = '0.75rem';
                locationRow.style.color = '#666';
                locationRow.style.marginTop = '2px';

                const leftSide = document.createElement('div');
                leftSide.style.display = 'flex';
                leftSide.style.flexDirection = 'column';
                leftSide.appendChild(nameSpan);
                leftSide.appendChild(locationRow);

                const typeSpan = document.createElement('span');
                typeSpan.className = 'mention-type';
                typeSpan.textContent = item.element_type;

                const iconSpan = document.createElement('span');
                iconSpan.textContent = getIconForType(item.element_type);

                const typeWithIcon = document.createElement('div');
                typeWithIcon.style.display = 'flex';
                typeWithIcon.style.alignItems = 'center';
                typeWithIcon.style.gap = '6px';
                typeWithIcon.appendChild(typeSpan);
                typeWithIcon.appendChild(iconSpan);

                const rowWrapper = document.createElement('div');
                rowWrapper.style.display = 'flex';
                rowWrapper.style.alignItems = 'center';
                rowWrapper.style.justifyContent = 'space-between';
                rowWrapper.style.width = '100%';
                rowWrapper.appendChild(leftSide);
                rowWrapper.appendChild(typeWithIcon);

                button.appendChild(rowWrapper);
                button.addEventListener('click', () => {
                  if (item.id === '__none__') return;
                  insertMentionCode(item, command, props, newEditor.view);
                });
                return button;
              };

              const updateSelection = () => {
                if (!component) return;
                component.innerHTML = '';

                const grouped: Record<string, MentionItem[]> = {};
                currentItems.forEach(item => {
                  const repo = item.git_repo_link || 'Other';
                  if (!grouped[repo]) grouped[repo] = [];
                  grouped[repo].push(item);
                });

                Object.entries(grouped).forEach(([repo, items]) => {
                  const header = createGroupHeader(repo);
                  component.appendChild(header);

                  if (expandedGroups.has(repo)) {
                    items.forEach((item, index) => {
                      const button = createMentionButton(item, currentCommand, currentProps, index === selectedIndex);
                      component.appendChild(button);
                    });
                  }
                });
              };

              return {
                onStart(props: SuggestionProps) {
                  currentProps = props;
                  selectedIndex = 0;
                  currentItems = props.items;
                  currentCommand = props.command;
                  component = document.createElement('div');
                  component.className = 'mention-dropdown';
                  updateSelection();
                  const referenceRect = props.clientRect?.();
                  if (!referenceRect) return;
                  popup = tippy('body', {
                    arrow: false,
                    getReferenceClientRect: () => referenceRect,
                    appendTo: () => document.body,
                    content: component,
                    showOnCreate: true,
                    interactive: true,
                    trigger: 'manual',
                    theme: 'light',
                    placement: 'bottom-start',
                    popperOptions: {
                      modifiers: [
                        { name: 'flip', options: { fallbackPlacements: ['top-start'] } },
                        { name: 'offset', options: { offset: [0, 6] } }
                      ]
                    }
                  })[0];
                },
                onUpdate(props: SuggestionProps) {
                  currentProps = props;
                  currentItems = props.items;

                  updateSelection();
                  const referenceRect = props.clientRect?.();
                  if (referenceRect) {
                    popup.setProps({ getReferenceClientRect: () => referenceRect });
                  }
                },
                onKeyDown({ event }) {
                  const count = currentItems.length;
                  if (count === 0) return false;
                  if (event.key === 'ArrowUp') {
                    selectedIndex = (selectedIndex - 1 + count) % count;
                    updateSelection();
                    return true;
                  }
                  if (event.key === 'ArrowDown') {
                    selectedIndex = (selectedIndex + 1) % count;
                    updateSelection();
                    return true;
                  }
                  if (event.key === 'Enter') {
                    const selected = currentItems[selectedIndex];
                     if (selected && selected.id !== '__none__') {
                        insertMentionCode(selected, currentCommand, currentProps, newEditor.view);
                      }
                    return true;
                  }
                  return false;
                },
                onExit() {
                  popup?.destroy?.();
                }
              };
            }
          }

        }),
      ],
      editable: !disabled,
      content: '',
      onUpdate: ({ editor }) => {
        const mentions: MentionItem[] = [];
        editor.state.doc.descendants((node: any) => {
          if (node.type.name === 'mention') {
            const match = mentionableElements.find(m => m.id === node.attrs.id);
            if (match && !mentions.some(m => m.id === match.id)) {
              mentions.push(match);
            }
          }
        });
        setSelectedMentions(mentions);
      }
    });

    setEditor(newEditor);
   
  }, [mentionableElements, disabled, editor, isMentionLoaded]);

  useImperativeHandle(ref, () => ({
    clearInput: () => {
      editor?.commands.clearContent();
      setSelectedMentions([]);
    }
  }), [editor]);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (mentionActiveRef.current) return;
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const text = editor?.getText().trim();
      if (text) {
        onSend(text);
        editor?.commands.clearContent();
      }
    }
  }, [editor, onSend]);


  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        background: '#fff',
        borderRadius: '50px',
        border: '2px solid #ddd',
        boxShadow: '0 1px 4px rgba(0,0,0,0.05)',
        padding: '20px 20px 50px 40px',
        margin: '0 auto',
        width: '100%',
        maxWidth: '90%',
      }}
    >
      {editor && (
        <EditorContent
          editor={editor}
          className="tiptap"
          style={{
            flexGrow: 1,
            outline: 'none',
            fontSize: '1.1rem',
            lineHeight: '1.5',
            fontWeight: 400,
            color: '#333',
            minHeight: '24px',
            maxHeight: '250px',
            overflowY: 'auto',
            overflowWrap: 'break-word',
            wordBreak: 'break-word',
            whiteSpace: 'pre-wrap',
          }}
          placeholder={placeholder}
        />
      )}
      <IconButton
        onClick={() => {
          const text = editor?.getText().trim();
          if (text) {
            onSend(text);
            editor?.commands.clearContent();
            setSelectedMentions([]);
          }
        }}
        disabled={disabled}
        size="large"
        color="primary"
      >
        <ArrowUpwardIcon sx={{ color: 'black' }} />
      </IconButton>
    </div>
  );
});

export default MessageInputWithMentions;
