import React, { useEffect, useState } from 'react';
import { useTable, useSortBy, Column } from 'react-table';
import axios from '../../http/axiosLLMConfig';
import '../../styles.css';
import { TableFormData } from '../types/constants'
import { FaPlay, FaSpinner, FaCheck } from 'react-icons/fa';
import { Table, TableBody, TableCell, TableHead, TableRow, TableSortLabel } from '@mui/material';

const ALL_COLUMNS = 'FULL'
const MANDATORY_COLUMNS = 'BASIC'

// Reusable table component
const ModelsTable: React.FC<{ columnsType: typeof ALL_COLUMNS | typeof MANDATORY_COLUMNS, data: TableFormData[], title: string }> = ({ columnsType, data, title }) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Initial': return 'grey';
      case 'In progress': return 'orange';
      case 'Finished': return 'green';
      default: return '';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'Initial': return <FaPlay style={{ color: 'grey' }} />;
      case 'In progress': return <FaSpinner style={{ color: 'orange' }} />;
      case 'Finished': return <FaCheck style={{ color: 'green' }} />;
      default: return null;
    }
  };

  const basicColumns: Column<TableFormData>[] = React.useMemo(
    () => [
      { Header: 'Base Model Name', accessor: 'baseModelName' },
      {
        Header: 'Status', accessor: 'status', Cell: ({ value }) => (
          <span style={{ color: getStatusColor(value) }}>
            {getStatusIcon(value)} {value}
          </span>
        ),
      },
    ],
    []
  );

  const fullColumns: Column<TableFormData>[] = React.useMemo(
    () => [
      {
        Header: 'Project Name', accessor: 'projectName', Cell: ({ row }: any) => (
          <span className={`project-name ${row.values.projectName}`}>
            {row.values.projectName}
          </span>
        )
      },
      { Header: 'Training Name', accessor: 'trainingName' },
      ...basicColumns,
      { Header: 'Tests Code Framework', accessor: 'testsCodeFramework' },
      { Header: 'In progress', accessor: 'progress' },
    ],
    []
  );

  const columns = columnsType == ALL_COLUMNS ? fullColumns : basicColumns
  const { getTableProps, headerGroups, rows, prepareRow } = useTable({ columns, data }, useSortBy);

  return (
    <div className="table-container">
      <h2>{title}</h2>
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
    </div>
  );
};


const AvailableRegisteredModels: React.FC = () => {
  const [data, setData] = useState<TableFormData[]>([]);

  const getStatusAndProgress = (modelType: string, checkpoint?: string) => {
    let percentageString: string = ''

    if (checkpoint) {
      // Split the string into numerator and denominator
      const [numerator, denominator] = checkpoint.split('/').map(Number);

      // Perform the division and convert to percentage
      const percentage = (numerator / denominator) * 100;

      // Format the result as a percentage string with two decimal places
      percentageString = percentage.toFixed(2) + '%';
    }

    switch (modelType) {
      case 'finetuned': return { status: 'Finished', progress: '100%' };
      case 'foundational': return { status: 'Available' };
      case 'checkpoint': return { status: 'In progress', progress: percentageString };
      default: return { status: 'Initial', progress: '0%' };
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get('/api/backend/getModels');
        const transformedData = response.data[0].adapters.map((item: any) => {
          return {
            projectName: item.project,
            trainingName: item.name.substring(0, 40),
            contextLength: item.context_length,
            baseModelName: response.data[0].base_model_name,
            modelType: item.project == "ALL"? 'foundational' : 'finetuned',
            testsCodeFramework: '-',
            status: "Finished",
            progress: '100%',
            checkpoint: item?.checkpoint || ''
          };
        });

          // Legendary Code (might be relevant again in the near future)
          // const transformedData = response.data.map((item: any) => {
          //   const { status, progress } = getStatusAndProgress(item.model_type, item?.checkpoint);
          //   return {
          //     projectName: item.project,
          //     trainingName: item.name.substring(0, 40),
          //     contextLength: item.context_length,
          //     baseModelName: item.base_model,
          //     modelType: item.model_type,
          //     testsCodeFramework: 'Robot',
          //     status,
          //     progress,
          //     checkpoint: item?.checkpoint
          //   };
          // });
        
        setData(transformedData);
      } catch (error) {
        console.error('Error fetching model data:', error);
      }
    };

    fetchData();
  }, []);

  const fineTunedModels = data.filter(model => model.modelType === 'finetuned' || model.modelType === 'checkpoint');
  const foundationalModels = data.filter(model => model.modelType === 'foundational');

  const TableToolTip = () =>
    <div className="tooltip-container">
      <h3 className="tooltip-header">Status Explanation</h3>
      <ul className="tooltip-list">
        <li><FaPlay style={{ color: 'grey' }} /> <strong style={{ color: 'grey' }}>Initial:&nbsp;</strong> Creating a dedicated project-specific parser to create a dataset to train the LLM with.</li>
        <li><FaSpinner style={{ color: 'orange' }} /> <strong style={{ color: 'orange' }}>In progress:&nbsp;</strong> Training the LLM with the new dataset.</li>
        <li><FaCheck style={{ color: 'green' }} /> <strong style={{ color: 'green' }}>Finished:&nbsp;</strong> LLM fine-tuned model is ready to use.</li>
      </ul>
    </div>

  return (
    <div className="table-container">
      <ModelsTable columnsType={ALL_COLUMNS} data={fineTunedModels} title="Fine Tuned Models" />
      <TableToolTip />
      <ModelsTable columnsType={MANDATORY_COLUMNS} data={foundationalModels} title="Foundational Models" />
    </div>
  );
};

export default AvailableRegisteredModels;
