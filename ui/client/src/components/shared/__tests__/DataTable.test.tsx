import { describe, it, expect } from "vitest";
import { screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DataTable, DataTableColumn } from "../DataTable";
import { render } from "@/test-utils/render";

type Row = { name: string };

const columns: DataTableColumn<Row>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ getValue }) => String(getValue()),
  },
];

const getBodyRows = () => {
  const tbody = document.querySelector("tbody");
  return tbody ? Array.from(tbody.querySelectorAll("tr")) : [];
};

describe("DataTable", () => {
  it("renders empty state when no data", () => {
    render(
      <DataTable
        columns={columns}
        data={[]}
        enablePagination={false}
        enableColumnFilters={false}
        enableGlobalFilter={false}
      />,
    );

    expect(screen.getByText("No data to display.")).toBeInTheDocument();
  });

  it("does not render global filter by default", () => {
    render(
      <DataTable
        columns={columns}
        data={[{ name: "Alice" }, { name: "Bob" }]}
        enableColumnFilters={false}
        enablePagination={false}
      />,
    );

    expect(
      screen.queryByPlaceholderText("Search all columns..."),
    ).not.toBeInTheDocument();
  });

  it("filters rows with a column filter input", async () => {
    const user = userEvent.setup();
    render(
      <DataTable
        columns={columns}
        data={[{ name: "Alice" }, { name: "Bob" }]}
        enableColumnFilters
        enableGlobalFilter={false}
        enablePagination={false}
      />,
    );

    await user.type(screen.getByPlaceholderText(/Filter/), "Ali");

    await waitFor(() => {
      const rows = getBodyRows();
      expect(rows).toHaveLength(1);
      expect(within(rows[0]).getByText("Alice")).toBeInTheDocument();
    });
  });

  it("paginates rows when next is clicked", async () => {
    const user = userEvent.setup();
    render(
      <DataTable
        columns={columns}
        data={[{ name: "First" }, { name: "Second" }]}
        enablePagination
        enableColumnFilters={false}
        enableGlobalFilter={false}
        initialState={{ pagination: { pageIndex: 0, pageSize: 1 } }}
      />,
    );

    expect(within(getBodyRows()[0]).getByText("First")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Next" }));

    expect(within(getBodyRows()[0]).getByText("Second")).toBeInTheDocument();
  });
});

