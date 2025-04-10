import React from "react";
import { Modal, Button } from "react-bootstrap";
import Highlight from "react-highlight";

const SqlModal = ({ show, onHide, sqlContent }) => {
  return (
    <Modal show={show} onHide={onHide} size="lg" centered>
      <Modal.Header closeButton>
        <Modal.Title>SQL Query</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <div className="bg-light p-3 rounded">
          <Highlight className="sql">{sqlContent}</Highlight>
        </div>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onHide}>
          Close
        </Button>
      </Modal.Footer>
    </Modal>
  );
};

export default SqlModal;
