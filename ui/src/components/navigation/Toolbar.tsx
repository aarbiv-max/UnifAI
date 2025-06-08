import React, { useState, useEffect, useRef } from 'react';
import { Menu, MenuItem, Button, FormControl, Select, SelectChangeEvent, ButtonGroup, InputLabel } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { DATA_SCIENCE_ROLE, USER_ROLE } from '../types/roles';
import RedHatLogoTAG from '../../assets/RedhatLogoNew.png';
import SendIcon from '@mui/icons-material/Send';
import HelpIcon from '@mui/icons-material/Help';
import { Collapse } from '@mui/material';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowRightIcon from '@mui/icons-material/KeyboardArrowRight';

interface ToolbarProps {
  role: string;
  setRole: (role: string) => void;
}

interface DropdownItem {
  label: string;
  path: string;
  disabled?: boolean;
}

interface DropdownItems {
  title: string;
  items: DropdownItem[];
  subItems?: DropdownItems[];
}

const dropdownAllItems: DropdownItems[] = [
  { title: 'About', items: [{ label: 'Welcome', path: '/' }, { label: 'Understanding AI', path: '/ai-content' }] },
  {title: 'Model Training', items: [], subItems: [
      {title: 'Parser', items: [{ label: 'Repository Parser', path: '/create-dataset' }, { label: 'Available Parsed Repositories', path: '/parsed-repos', disabled: true }]},
      {title: 'Dataset Generation', items: [{label: 'Preparing Dataset', path: '/prepare-dataset' }, {label: 'Dataset Progress', path: '/deployed-datasets' }, {label: 'Available Datasets', path: '/ready-datasets', disabled: true }]},
      {title: 'Fine-tuning', items: [{label: 'Train New Model', path: '/train-form' }, {label: 'Training Progress', path: '/deployed-training' }, {label: 'Trained Models', path: '/available-trained'}, {label: 'Registered Models', path: '/available-registered' }]}
  ]},
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
  const [selectedButton, setSelectedButton] = useState<string | null>(null);
  const toolbarRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate(); 
  const [expandedDropdown, setExpandedDropdown] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);


  useEffect(() => {
    role === DATA_SCIENCE_ROLE ? setDropdownList(dropdownAllItems) : setDropdownList(dropdownUserItems);
  }, [role]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      const clickedOutsideToolbar = toolbarRef.current && !toolbarRef.current.contains(target);
      const clickedOutsideMenu = menuRef.current && !menuRef.current.contains(target);
  
      if (clickedOutsideToolbar && clickedOutsideMenu) {
        setSelectedButton(null);
        setAnchorEl(null);
        setExpandedDropdown(null);
      }
    };
  
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleClick = (event: React.MouseEvent<HTMLElement>, title: string) => {
    setAnchorEl(event.currentTarget);
    setSelectedButton(title);
  };

  const handleMenuItemClick = (item: DropdownItem) => {
    navigate(item.path);
    setAnchorEl(null); 
    setExpandedDropdown(null)
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

      {/* Main Menu */}
      {dropdownList.map((dropdown) => (
        <Menu
          key={dropdown.title}
          anchorEl={anchorEl}
          open={selectedButton === dropdown.title && Boolean(anchorEl)}
          onClose={() => {
            setAnchorEl(null);
            setExpandedDropdown(null);
          }}
          slotProps={{ paper: {style: { position: 'absolute' }, ref: menuRef} }}
        >
          {/* Render regular items */}
          {dropdown.items.map((item) => (
            <MenuItem key={item.label} onClick={(event) => handleMenuItemClick(item)}>
              {item.label}
            </MenuItem>
          ))}

          {/* Render collapsible items */}
          {dropdown.subItems?.map((subItem) => (
            <React.Fragment key={subItem.title}>
              <MenuItem
                onClick={(event) => {
                  setExpandedDropdown((prev) => (prev === subItem.title ? null : subItem.title));
                }}
              >
                {subItem.title}
                {expandedDropdown === subItem.title ? <KeyboardArrowDownIcon /> : <KeyboardArrowRightIcon />}
              </MenuItem>
              <Collapse in={expandedDropdown === subItem.title} timeout="auto" unmountOnExit>
                {subItem.items.map((item) => (
                  <MenuItem
                  key={item.label}
                  onClick={() => !item.disabled && handleMenuItemClick(item)}
                  style={{
                    paddingLeft: '2rem',
                    opacity: item.disabled ? 0.5 : 1,
                    pointerEvents: item.disabled ? 'none' : 'auto',
                  }}
                  disabled={item.disabled}
                >
                  {item.label}
                </MenuItem>
              ))}
              </Collapse>
            </React.Fragment>
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