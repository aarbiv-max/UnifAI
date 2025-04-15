import React, { useState, useEffect, useRef } from 'react';
import { Menu, MenuItem, Button, FormControl, Select, SelectChangeEvent, ButtonGroup, InputLabel } from '@mui/material';
import { useNavigate } from 'react-router-dom'; // Import useNavigate
import { DATA_SCIENCE_ROLE, USER_ROLE } from '../types/roles';
import RedHatLogoTAG from '../../assets/RedhatLogoNew.png';
import SendIcon from '@mui/icons-material/Send';
import HelpIcon from '@mui/icons-material/Help';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';

interface ToolbarProps {
  role: string;
  setRole: (role: string) => void;
}

interface DropdownItem {
  label: string;
  path: string;
}

interface DropdownItems {
  title: string;
  items: DropdownItem[];
}

const dropdownAllItems: DropdownItems[] = [
  { title: 'About', items: [{ label: 'Welcome', path: '/' }, { label: 'Understanding AI', path: '/ai-content' }] },
  { title: 'Dataset', items: [{ label: 'Creating Dataset', path: '/create-dataset' },{ label: 'Preparing Dataset', path: '/prepare-dataset' }, { label: 'Dataset Progress', path: '/deployed-datasets' }, { label: 'Available Datasets', path: '/dataset-table' }] },  { title: 'Training', items: [{ label: 'Train New Model', path: '/train-form' }, { label: 'Available Trained Models', path: '/form-table' }] },
  { title: 'Inference', items: [{ label: 'Generate Automatic Test', path: '/chatbot' }, { label: 'Saved Prompts', path: '/saved-prompts' }] },
  { title: 'Statistics', items: [{ label: 'Graphs', path: '/statistics' }] },
];

const dropdownUserItems: DropdownItems[] = [
  { title: 'About', items: [{ label: 'Welcome', path: '/' }, { label: 'Understanding AI', path: '/ai-content' }] },
  { title: 'Inference', items: [{ label: 'Generate Automatic Test', path: '/chatbot' }, { label: 'Saved Prompts', path: '/saved-prompts' }] },
  { title: 'Statistics', items: [{ label: 'Graphs', path: '/statistics' }] },
];

const Toolbar: React.FC<ToolbarProps> = ({ role, setRole }) => {
  const [dropdownList, setDropdownList] = useState<DropdownItems[]>(dropdownUserItems);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [menuTitle, setMenuTitle] = useState<string>('');
  const [selectedButton, setSelectedButton] = useState<string | null>(null);
  const toolbarRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate(); // Use navigate for routing

  useEffect(() => {
    role === DATA_SCIENCE_ROLE ? setDropdownList(dropdownAllItems) : setDropdownList(dropdownUserItems);
  }, [role]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (toolbarRef.current && !toolbarRef.current.contains(event.target as Node)) {
        setSelectedButton(null);
        setAnchorEl(null);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleClick = (event: React.MouseEvent<HTMLElement>, title: string) => {
    setAnchorEl(event.currentTarget);
    setMenuTitle(title);
    setSelectedButton(title);
  };

  const handleMenuItemClick = (item: DropdownItem) => {
    navigate(item.path); // Navigate to the selected page
    setAnchorEl(null);
    setSelectedButton(null);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleRoleChange = (event: SelectChangeEvent) => {
    setRole(event.target.value);
  };

  return (
    <div className="toolbar" ref={toolbarRef}>
      <div className="left-section">
        <a href="/">
          <img src={RedHatLogoTAG} alt="Logo" className="logo-image" />
        </a>
        <ButtonGroup variant="contained" className="dropdown-buttons" aria-label="Basic button group">
          {dropdownList.map((dropdown) => (
            <Button
              key={dropdown.title}
              endIcon={<KeyboardArrowDownIcon />}
              onClick={(event) => handleClick(event, dropdown.title)}
              className={selectedButton === dropdown.title ? 'selected' : ''}
            >
              {dropdown.title}
            </Button>
          ))}
        </ButtonGroup>
      </div>

      {dropdownList.map((dropdown) => (
        <Menu
          key={dropdown.title}
          anchorEl={anchorEl}
          open={menuTitle === dropdown.title && Boolean(anchorEl)}
          onClose={handleMenuClose}
        >
          {dropdown.items.map((item) => (
            <MenuItem
              key={item.label}
              onClick={() => handleMenuItemClick(item)}
            >
              {item.label}
            </MenuItem>
          ))}
        </Menu>
      ))}

      <div className="toolbar-buttons">
        <FormControl variant="outlined" className="role-selection">
          <InputLabel>Role Selection</InputLabel>
          <Select value={role} onChange={handleRoleChange}>
            <MenuItem value={USER_ROLE}>User Role</MenuItem>
            <MenuItem value={DATA_SCIENCE_ROLE}>Data Science Role</MenuItem>
          </Select>
        </FormControl>
        <Button disabled variant="contained" className="end-button" endIcon={<SendIcon />}>Log In</Button>
        <Button disabled variant="contained" className="end-button" endIcon={<HelpIcon />}>Support</Button>
      </div>
    </div>
  );
};

export default Toolbar;
