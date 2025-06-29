import React, { useEffect, useState } from 'react';
import { useTable, useSortBy, Column } from 'react-table';
import axios from '../../http/axiosLLMConfig';
import { FaEye } from 'react-icons/fa';
import '../../styles.css';
import { Table, TableBody, TableCell, TableHead, TableRow, TableSortLabel } from '@mui/material';

interface RepoFileData {
  name: string;
}

const DataSetTable: React.FC = () => {
  const [data, setData] = useState<RepoFileData[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get('/api/backend/getHfRepoFiles?repoId=oodeh/NcsRobotTestFramework&repoType=dataset');
        // Convert the array of file names to an array of objects with a 'name' property
        const transformedData = response.data.map((fileName: string) => ({ name: fileName }));
        setData(transformedData);
      } catch (error) {
        console.error('Error fetching repository files:', error);
      }
    };

    fetchData();
  }, []);

  const columns: Column<RepoFileData>[] = React.useMemo(
    () => [
      {
        Header: 'Name',
        accessor: 'name',
        id: 'fileName',  // Assign a unique id to this column
      },
      {
        Header: 'View',
        accessor: 'name',
        id: 'view',  // Assign a unique id to this column
        Cell: ({ value }) => (
          <span onClick={() => setSelectedFile(value)} style={{ cursor: 'pointer' }}>
            <FaEye />
          </span>
        ),
      },
    ],
    []
  );

  const { getTableProps, getTableBodyProps, headerGroups, rows, prepareRow } = useTable({ columns, data }, useSortBy);

  return (
    <div className="table-container">
      <h2>Dataset Files</h2>
      <Table {...getTableProps()} className="forms-table">
        <TableHead>
          {headerGroups.map((headerGroup: any) => (
            <TableRow {...headerGroup.getHeaderGroupProps()}>
              {headerGroup.headers.map((column: any) => (
                <TableCell {...column.getHeaderProps()}>
                  <TableSortLabel
                    active={column.isSorted}
                    direction={column.isSortedDesc ? 'desc' : 'asc'}
                    {...column.getSortByToggleProps()}
                  >
                    {column.render('Header')}
                  </TableSortLabel>
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableHead>
        <TableBody>
          {rows.map((row: any) => {
            prepareRow(row);
            return (
              <TableRow {...row.getRowProps()}>
                {row.cells.map((cell: any) => (
                  <TableCell
                    {...cell.getCellProps()}
                    className="table-cell"
                    onMouseEnter={(e) => {
                      const columnIndex = cell.column.id;
                      const cells = document.querySelectorAll(
                        `td[data-column-id="${columnIndex}"]`
                      );
                      cells.forEach(
                        (cell) =>
                          (cell as HTMLElement).style.backgroundColor =
                          'rgba(46, 120, 199, 0.2)'
                      );
                    }}
                    onMouseLeave={(e) => {
                      const columnIndex = cell.column.id;
                      const cells = document.querySelectorAll(
                        `td[data-column-id="${columnIndex}"]`
                      );
                      cells.forEach(
                        (cell) => (cell as HTMLElement).style.backgroundColor = ''
                      );
                    }}
                    data-column-id={cell.column.id}
                  >
                    {cell.render('Cell')}
                  </TableCell>
                ))}
              </TableRow>
            );
          })}
        </TableBody>
      </Table>

      {selectedFile && (
        <div className="iframe-container">
          <iframe
            src={`https://huggingface.co/datasets/oodeh/NcsRobotTestFramework/embed/viewer?file=${encodeURIComponent(selectedFile)}`}
            width="100%"
            height="560px"
          ></iframe>
        </div>
      )}
    </div>
  );
};

export default DataSetTable;